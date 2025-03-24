import os
import subprocess
import xarray as xr
import pandas as pd
import numpy as np

year = 2019
# 처리할 변수 목록: "salt", "temp", "flow"
variables = ['salt', 'temp', 'flow']

input_dir = rf"H:\Dropbox\y2025\01_Atlantis\06_hydro\branches\s1\{year}"
output_dir = rf"H:\Dropbox\y2025\01_Atlantis\06_hydro\branches\s1\{year}"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for var in variables:
    total_time_steps = 0
    print(f"\n===== {var} 처리 시작 =====")
    
    # 1. 월별 텍스트 파일을 NetCDF 파일로 변환
    for month in range(1, 13):
        month_str = f"{month:02d}"
        txt_file = os.path.join(input_dir, f"{var}_{year}_{month_str}.txt")
        nc_file = os.path.join(output_dir, f"{var}_{year}_{month_str}.nc")
    
        if not os.path.exists(txt_file):
            print(f"파일이 존재하지 않음: {txt_file}")
            continue
    
        cmd = ["ncgen", "-o", nc_file, txt_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"변환 오류 {txt_file}:\n{result.stderr}")
        else:
            print(f"변환 완료: {txt_file} -> {nc_file}")
    
            try:
                ds = xr.open_dataset(nc_file, engine='netcdf4')
                time_steps = ds.sizes['t']  # ds.dims['t'] 대신 ds.sizes['t'] 사용
                print(f"{nc_file} 파일에 {time_steps}개의 시간 단계가 포함됨.")
                total_time_steps += time_steps
                ds.close()
            except Exception as e:
                print(f"{nc_file}의 't' 차원을 읽는 중 오류 발생: {e}")
    
    print(f"{var} 파일에서 추출한 총 time step 개수: {total_time_steps}")
    
    # 2. 12시간 간격의 날짜 벡터 생성
    start_time = pd.to_datetime(f"{year}-01-01 00:00:00")
    end_time = pd.to_datetime(f"{year}-12-31 12:00:00")
    time_vector = pd.date_range(start=start_time, end=end_time, freq="12h")  # 'H' 대신 'h' 사용
    
    # 기준 시간 설정
    ref_time = pd.to_datetime(f"{year}-01-01 00:00:00")
    seconds_values_full = (time_vector - ref_time).total_seconds()
    
    # 3. 생성된 월별 NetCDF 파일 병합
    merged_file = os.path.join(output_dir, f"{var}_{year}.nc")
    
    # 파일 존재 여부 확인
    file_list = [os.path.join(output_dir, f"{var}_{year}_{month:02d}.nc") for month in range(1, 13)]
    existing_files = [f for f in file_list if os.path.exists(f)]
    
    if len(existing_files) != 12:
        raise ValueError(f"총 12개 파일이 필요하지만 {len(existing_files)}개만 발견됨: {existing_files}")
    
    try:
        ds_merged = xr.open_mfdataset(existing_files, combine='nested', concat_dim='t', engine='netcdf4')
    
        if ds_merged.dims['t'] != len(seconds_values_full):
            raise ValueError(f"병합된 데이터셋의 t 차원 ({ds_merged.dims['t']})이 예상값 ({len(seconds_values_full)})과 다릅니다.")
        else:
            ds_merged = ds_merged.assign_coords(t=("t", seconds_values_full.astype(np.float64)))
            ds_merged["t"].attrs["units"] = f"seconds since {year}-01-01 00:00:00"
            ds_merged["t"].attrs["dt"] = 43200.0
    
        ds_merged.to_netcdf(merged_file)
        print(f"최종 NetCDF 파일 생성 완료: {merged_file}")
    
    except Exception as e:
        print(f"NetCDF 병합 중 오류 발생: {e}")
    
    print(f"===== {var} 처리 완료 =====\n")
