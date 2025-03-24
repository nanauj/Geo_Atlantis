# -*- coding: utf-8 -*-
"""
Modified on Wed Mar 19 2025

@author: Ukjae
"""

import os
import scipy.io
import netCDF4 as nc
import numpy as np
import pandas as pd

# 기본 변수 설정
year = 2019

# 데이터 파일 경로 설정
base_path = r"D:\Dropbox\y2025\01_Atlantis\05_hycom"
fpath = os.path.join(base_path, str(year))
fnameTemp = f"av_temp_{year}.mat"
fnameSalt = f"av_salt_{year}.mat"

# .mat 파일 로드
mat_file_name1 = os.path.join(fpath, fnameTemp)
av_temp_data = scipy.io.loadmat(mat_file_name1)
mat_file_name2 = os.path.join(fpath, fnameSalt)
av_salt_data = scipy.io.loadmat(mat_file_name2)

# mat 파일 내 변수 (형상: [boxes, time, level]로 가정)
temp = av_temp_data['av_temp']
salt = av_salt_data['av_salt']
vflux = salt * 0  # 강제 0으로 초기화

# 차원 정보
n_time = np.size(temp, 1)  # 729 (12시간 간격 1년치)
n_boxes = 232
n_levels = 6


# 12시간 간격의 날짜·시간 시리즈 생성 
start_time = pd.to_datetime(f"{year}-01-01 00:00:00")
end_time = pd.to_datetime(f"{year}-12-31 12:00:00")
time_vector = pd.date_range(start=start_time, end=end_time, freq="12H")

if len(time_vector) != n_time:
    print(f"Warning: 예상 time 스탭 {n_time}개와 생성된 스탭 {len(time_vector)}개가 일치하지 않습니다.")


# mat 파일에서 불러온 데이터는 [boxes, time, level] 형태이므로, 최종 NetCDF에 맞게 [time, boxes, level]로 전치
temp_full = np.transpose(temp, (1, 0, 2))
salt_full = np.transpose(salt, (1, 0, 2))
vflux_full = np.transpose(vflux, (1, 0, 2))

# 월별로 분할하여 NetCDF 파일로 저장 (월별 파일명 예: avs_2021_01.nc)
for month in range(1, 13):
    # time_vector에서 해당 월에 해당하는 인덱스 추출
    month_mask = time_vector.month == month
    month_indices = np.where(month_mask)[0]
    if len(month_indices) == 0:
        continue  # 해당 월 데이터가 없으면 건너뜀

    subset_time_vector = time_vector[month_mask]

    # 각 월의 첫째 날을 기준으로 경과일(day) 계산
    month_ref_time = pd.to_datetime(f"{year}-{month:02d}-01 00:00:00")
    subset_days = (subset_time_vector - month_ref_time).days + (subset_time_vector - month_ref_time).seconds / 86400.0
    
    subset_temp = temp_full[month_mask, :, :]  # shape: (n_time_month, boxes, levels)
    subset_salt = salt_full[month_mask, :, :]
    subset_vflux = vflux_full[month_mask, :, :]

    # NetCDF 파일 생성 (예: "avs_2021_01.nc", "avs_2021_02.nc", …)
    nc_filename = os.path.join(fpath, f"avs_{year}_{month:02d}.nc")
    if os.path.exists(nc_filename):
        os.remove(nc_filename)
    ds = nc.Dataset(nc_filename, 'w', format='NETCDF4')

    # 차원 생성
    ds.createDimension('time', None)
    ds.createDimension('level', n_levels)
    ds.createDimension('boxes', n_boxes)

    # 변수 생성
    time_var = ds.createVariable('time', 'd', ('time',))
    level_var = ds.createVariable('level', 'i', ('level',))
    boxes_var = ds.createVariable('boxes', 'i', ('boxes',))
    temperature_var = ds.createVariable('temperature', 'f', ('time', 'boxes', 'level',))
    salinity_var = ds.createVariable('salinity', 'f', ('time', 'boxes', 'level',))
    verticalflux_var = ds.createVariable('verticalflux', 'f', ('time', 'boxes', 'level',))

    # 변수 속성 지정
    time_var.long_name = 'time'
    time_var.units = 'days since 2019-01-01 00:00:00'
    time_var.calendar = 'gregorian'
    time_var.dt = 43200  # 12시간 간격이므로 0.5일

    boxes_var.long_name = 'Box IDs'

    level_var.long_name = 'layer index; 1=near-surface'
    level_var.positive = 'down'

    temperature_var.long_name = 'temperature volume averaged'
    temperature_var.units = 'degree_C'
    temperature_var.FillValue = -10e20

    salinity_var.long_name = 'salinity volume averaged'
    salinity_var.units = '1e-3'
    salinity_var.FillValue = -10e20

    verticalflux_var.long_name = 'vertical flux averaged over floor of box'
    verticalflux_var.positive = 'upward'
    verticalflux_var.units = 'm^3/s'
    verticalflux_var.FillValue = -10e20

    # 변수 데이터 할당
    boxes_var[:] = np.arange(n_boxes)
    level_var[:] = np.arange(1, n_levels + 1)
    time_var[:] = subset_days
    temperature_var[:, :, :] = subset_temp
    salinity_var[:, :, :] = subset_salt
    verticalflux_var[:, :, :] = subset_vflux

    ds.close()
    print(f"Saved month {month:02d} data to {nc_filename}")
