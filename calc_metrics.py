#!/usr/bin/env python3
import sys

def parse_perf_csv(filepath):
    data_points = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip(): continue
                parts = line.split(',')
                if len(parts) < 2: continue
                try:
                    ts = float(parts[0])
                    val_str = parts[1]
                    val = 0.0
                    if val_str != '<not supported>' and val_str != '<not counted>':
                        val = float(val_str)
                    
                    evt = parts[-1].strip()
                    if len(parts) > 3 and parts[2].strip() in ['Joules', 'Watts', 'Seconds']:
                        evt = parts[3].strip()
                    elif len(parts) >= 3:
                         if parts[2].strip() == "": evt = parts[3].strip()
                         else: evt = parts[2].strip()

                    data_points.append({'time': ts, 'event': evt, 'count': val})
                except: continue
    except Exception as e:
        print(f'{{"error": "{str(e)}"}}')
        sys.exit(1)
    return data_points

def main():
    if len(sys.argv) < 3: return
    filepath = sys.argv[1]
    arch = sys.argv[2]
    
    # [新增] 获取用户输入的间隔 (例如 "2s" 或 "2.0")
    user_interval = "1s" # 默认值
    if len(sys.argv) > 3:
        user_interval = sys.argv[3]

    raw_data = parse_perf_csv(filepath)
    if not raw_data: 
        print('{"error": "No data parsed"}')
        return

    aggregated_data = {}
    for item in raw_data:
        t = item['time']
        if t not in aggregated_data: aggregated_data[t] = {}
        aggregated_data[t][item['event']] = item['count']

    timestamps = sorted(aggregated_data.keys())
    if len(timestamps) < 1: 
        print('{"error": "No timestamps found"}')
        return
    
    # [逻辑] 总时长 = 实际测量的最后一个时间戳
    actual_run_time = timestamps[-1]

    # [逻辑] 直接累加 (Direct Sum of Deltas)
    total_bops_sum = 0.0
    
    for t in timestamps:
        events = aggregated_data[t]
        step_uops = 0.0
        step_br = 0.0
        step_mem = 0.0
        
        if arch == "x86":
            step_uops = events.get('uops_executed.core', 0.0)
            step_br   = events.get('br_inst_retired.all_branches', 0.0)
            step_mem  = events.get('mem_inst_retired.all_loads', 0.0) + \
                        events.get('mem_inst_retired.all_stores', 0.0)
        elif arch == "arm":
            step_uops = events.get('inst_retired', 0.0)
            step_br   = events.get('br_retired', 0.0)
            step_mem  = events.get('l1d_cache_refill', 0.0) + \
                        events.get('l1d_cache_wb', 0.0)
        
        step_val = step_uops - step_br - step_mem
        if step_val > 0:
            total_bops_sum += step_val

    # [输出]
    print(f'{{')
    print(f'  "arch": "{arch}",')
    print(f'  "interval": "{user_interval}",')
    # 3. 算出来的总和
    print(f'  "BOPs": {int(total_bops_sum)}')
    print(f'}}')

if __name__ == "__main__":
    main()
