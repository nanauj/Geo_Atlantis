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
from datetime import datetime as dt

# -----------------------------------------------------------------
# 1. .mat 파일 로드 및 데이터 전처리
# -----------------------------------------------------------------
year = 2019
base_path  = r"D:\Dropbox\y2025\01_Atlantis\05_hycom"
fpath      = os.path.join(base_path, str(year))
fnameTrans = f"trans_new_{year}.mat"
fnameBMG   = 'bgm_v2.mat'

mat_file_name1 = os.path.join(fpath, fnameTrans)
trans_data     = scipy.io.loadmat(mat_file_name1)

mat_file_name2 = os.path.join(base_path, fnameBMG)
face_data      = scipy.io.loadmat(mat_file_name2)

# trans: shape = (n_faces, n_time, n_levels) = (548, 729, 6)
trans = trans_data['T']
lrdata = face_data['lr']
pdata1 = face_data['pt1']
pdata2 = face_data['pt2']

# 차원 정보
n_faces  = 548
n_time   = np.size(trans, 1)  # 729 (12시간 간격 1년치)
n_levels = 6

# 12시간 간격의 날짜·시간 시리즈 생성 (2019년 1월 1일부터 12월 31일까지)
start_time = pd.to_datetime(f"{year}-01-01 00:00:00")
end_time   = pd.to_datetime(f"{year}-12-31 12:00:00")
time_vector = pd.date_range(start=start_time, end=end_time, freq="12H")


# trans 데이터의 차원 변환: (548,729,6) -> (729,548,6)
trans2 = np.transpose(trans, (1, 0, 2))

# -----------------------------------------------------------------
# 2. 월별로 NetCDF 파일 생성
# -----------------------------------------------------------------
for month in range(1, 13):
    # 해당 월에 해당하는 인덱스 추출
    month_mask    = time_vector.month == month
    month_indices = np.where(month_mask)[0]
    if len(month_indices) == 0:
        continue  # 해당 월 자료가 없으면 건너뜀


    subset_time_vector = time_vector[month_mask]

    # 각 월의 첫째 날을 기준으로 경과일(day) 계산
    month_ref_time = pd.to_datetime(f"{year}-{month:02d}-01 00:00:00")
    subset_days = (subset_time_vector - month_ref_time).days + (subset_time_vector - month_ref_time).seconds / 86400.0


    subset_trans       = trans2[month_mask, :, :]  # shape: (n_time_month, 548, 6)

    # 월별 NetCDF 파일명 생성 (예: "trans_2019_01.nc", "trans_2019_02.nc", …)
    nc_filename = os.path.join(fpath, f"trans_{year}_{month:02d}.nc")
    if os.path.exists(nc_filename):
        os.remove(nc_filename)
    ds = nc.Dataset(nc_filename, 'w', format='NETCDF4')

    # 차원 생성
    ds.createDimension('time', None)
    ds.createDimension('level', n_levels)
    ds.createDimension('faces', n_faces)

    # 변수 생성
    time_var     = ds.createVariable('time', 'd', ('time',))
    level_var    = ds.createVariable('level', 'i', ('level',))
    faces_var    = ds.createVariable('faces', 'i', ('faces',))
    pt1_x        = ds.createVariable('pt1_x', 'f', ('faces',))
    pt1_y        = ds.createVariable('pt1_y', 'f', ('faces',))
    pt2_x        = ds.createVariable('pt2_x', 'f', ('faces',))
    pt2_y        = ds.createVariable('pt2_y', 'f', ('faces',))
    dest_boxid   = ds.createVariable('dest_boxid', 'i', ('faces',))
    source_boxid = ds.createVariable('source_boxid', 'i', ('faces',))
    transport    = ds.createVariable('transport', 'f', ('time', 'faces', 'level',))

    # 변수 속성 지정
    time_var.long_name = 'time'
    time_var.units     = 'days since 2019-01-01 00:00:00'
    time_var.calendar  = 'gregorian'
    time_var.dt        = 43200  # 12시간 간격이므로 0.5일

    faces_var.long_name = 'Face IDs'
    level_var.long_name = 'layer index; 1=near-surface'
    level_var.positive  = 'down'

    pt1_x.long_name = 'x coordinate of point 1 of face'
    pt1_x.units     = 'degree_east'
    pt1_y.long_name = 'y coordinate of point 1 of face'
    pt1_y.units     = 'degree_north'
    pt2_x.long_name = 'x coordinate of point 2 of face'
    pt2_x.units     = 'degree_east'
    pt2_y.long_name = 'y coordinate of point 2 of face'
    pt2_y.units     = 'degree_north'

    dest_boxid.long_name = 'ID of destination box'
    dest_boxid.units     = 'id'
    source_boxid.long_name = 'ID of source box'
    source_boxid.units     = 'id'

    transport.long_name = 'flux across face'
    transport.units     = '10^6 m^3/s (= sv)'
    transport.comment   = '+ve is to left, viewing from pt1 to pt2'
    transport.FillValue = 0

    # 변수 데이터 할당
    time_var[:]     = subset_days
    faces_var[:]    = np.arange(n_faces)
    level_var[:]    = np.arange(1, n_levels + 1)
    pt1_x[:]        = pdata1[:, 0]
    pt1_y[:]        = pdata1[:, 1]
    pt2_x[:]        = pdata2[:, 0]
    pt2_y[:]        = pdata2[:, 1]
    dest_boxid[:]   = lrdata[:, 0]
    source_boxid[:] = lrdata[:, 1]
    transport[:, :, :] = subset_trans

    ds.close()
    print(f"Saved month {month:02d} data to {nc_filename}")
