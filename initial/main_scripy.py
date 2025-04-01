# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 14:03:58 2025

@author: Ukjae
"""

from atlantis_init_tools import make_init_csv, get_init_nc

# 누적 깊이
cum_depths = [0, 10, 50, 200, 600, 1500, 3000]

# 입력 파일
grp_file = "KOR_FGROUP2.csv"
bgm_file = "version2_utm_relax.bgm"
csv_name = "GBRtemplate"
nc_file = "GBRtemplate.nc"
# vert_file = "vertical_distribution.csv"  # optional

# 초기 CSV 템플릿 만들기
make_init_csv(grp_file, bgm_file, cum_depths, csv_name, ice_model=True)

# 현재 모듈에는 make_init_nc 함수가 없으므로 NetCDF 파일 생성을 위한 함수 호출은 주석 처리합니다.
# 만약 make_init_nc 함수의 구현이 필요하면, 해당 기능을 atlantis_init_tools.py에 추가해야 합니다.
# make_init_nc(bgm_file, cum_depths, f"{csv_name}_init.csv", f"{csv_name}_horiz.csv", nc_file, vert_file=None, ice_model=True)

# NetCDF에서 값 추출해서 CSV로 저장
get_init_nc(nc_file, "initial_conditions_output.csv")
