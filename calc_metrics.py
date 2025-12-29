#!/usr/bin/env python3
import sys
import os

def parse_perf_csv(filepath):
    """
    解析 perf -x , -I ... 输出的 CSV 文件。
    返回一个列表，其中每个元素是一个字典，代表一个时间点的数据。
    结构: { timestamp: float, events: { event_name: count, ... } }
    """
    data_points = []
    current_timestamp = None
    current_events = {}

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                if len(parts) < 3:
                    continue
                
                try:
                    # perf -I 输出格式: timestamp, count, unit, event_name, ...
                    # 某些版本可能是 timestamp, count, event_name
                    ts = float(parts[0])
                    count_str = parts[1]
                    if count_str == '<not supported>':
                        count = 0.0
                    else:
                        count = float(count_str)
                    
                    # 事件名称通常在第3列 (索引2) 或第4列 (索引3，如果有单位)
                    # 我们从后往前找，或者通过排除法
                    # 这里假设最后一部分是事件名，去掉可能的修饰符
                    event_name = parts[2] if len(parts) == 3 else parts[3]
                    # 清理事件名中的空格
                    event_name = event_name.strip()

                    if current_timestamp != ts:
                        if current_timestamp is not None:
                            data_points.append({'time': current_timestamp, 'events': current_events})
                        current_timestamp = ts
                        current_events = {}
                    
                    current_events[event_name] = count

                except ValueError:
                    continue
            
            # 添加最后一个点
            if current_timestamp is not None:
                data_points.append({'time': current_timestamp, 'events': current_events})
                
    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)
        
    return data_points

def calc_x86(last_events, duration):
    """
    x86 计算公式
    """
    # 1. 计算 BOPs
    # 公式: (uops - (branches + loads + stores)) / (time * 1e9) 
    uops = last_events.get('uops_executed.core', 0)
    branches = last_events.get('br_inst_retired.all_branches', 0)
    loads = last_events.get('mem_inst_retired.all_loads', 0)
    stores = last_events.get('mem_inst_retired.all_stores', 0)
    
    bops_numerator = uops - (branches + loads + stores)
    bops = bops_numerator / (duration * 1e9) if duration > 0 else 0

    # 2. 计算 GFLOPS [cite: 20-35]
    # 权重表
    weights = {
        'fp_arith_inst_retired.scalar_double': 1,
        'fp_arith_inst_retired.128b_packed_double': 2,
        'fp_arith_inst_retired.256b_packed_double': 4,
        'fp_arith_inst_retired.512b_packed_double': 8,
        'fp_arith_inst_retired.scalar_single': 1,
        'fp_arith_inst_retired.128b_packed_single': 4,
        'fp_arith_inst_retired.256b_packed_single': 8,
        'fp_arith_inst_retired.512b_packed_single': 16
    }
    
    weighted_sum = 0
    for event, weight in weights.items():
        weighted_sum += last_events.get(event, 0) * weight
        
    gflops = weighted_sum / (duration * 1e9) if duration > 0 else 0
    
    return bops, gflops

def calc_arm(last_events, duration):
    """
    ARM 计算公式
    """
    # 1. 计算 BOPs 
    # 公式: (inst_retired - (br_retired + mem_access)) / (time * 1e9)
    # 注意: Shell 脚本中 mem_access 由 l1d_cache_refill 和 l1d_cache_wb 组成
    inst = last_events.get('inst_retired', 0)
    br = last_events.get('br_retired', 0)
    l1_refill = last_events.get('l1d_cache_refill', 0)
    l1_wb = last_events.get('l1d_cache_wb', 0)
    mem_access = l1_refill + l1_wb
    
    bops_numerator = inst - (br + mem_access)
    bops = bops_numerator / (duration * 1e9) if duration > 0 else 0
    
    # 2. GFLOPS: 无法计算 
    return bops, 0.0

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 calc_metrics.py <bops_file> <arch>")
        sys.exit(1)

    filepath = sys.argv[1]
    arch = sys.argv[2] # "x86" or "arm"

    data = parse_perf_csv(filepath)
    
    if len(data) < 2:
        print("Error: Not enough data points to calculate interval duration.")
        sys.exit(1)

    # 获取最后两个时间点 [cite: 6-7]
    last_point = data[-1]
    prev_point = data[-2]
    
    # 第1步: 计算间隔时长 
    duration = last_point['time'] - prev_point['time']
    
    if duration <= 0:
        print("Error: Invalid interval duration.")
        sys.exit(1)

    bops = 0.0
    gflops = 0.0

    if arch == "x86":
        bops, gflops = calc_x86(last_point['events'], duration)
    elif arch == "arm":
        bops, gflops = calc_arm(last_point['events'], duration)
    else:
        print(f"Unknown architecture: {arch}")
        sys.exit(1)

    # 输出结果 (JSON 格式，方便 Shell 解析或直接查看)
    print(f"{{")
    print(f"  \"arch\": \"{arch}\",")
    print(f"  \"interval_duration\": {duration:.6f},")
    print(f"  \"BOPs\": {bops:.6f},")
    if arch == "x86":
        print(f"  \"GFLOPS\": {gflops:.6f}")
    else:
        print(f"  \"GFLOPS\": \"N/A\"")
    print(f"}}")

if __name__ == "__main__":
    main()
