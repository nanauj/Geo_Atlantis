# -*- coding: utf-8 -*-
"""
Created on Wed Mar  5 15:49:09 2025

@author: Ukjae

자동화 스크립트: 매 월별로 param 파일 수정 후 hydroconstruct.exe 실행 및
임시 run.bat 파일을 생성하여 출력 파일 이름을 바로 flux_년도_월.txt 등으로 생성
Created on 2025-02-27
"""

import os
import subprocess
import pandas as pd
import calendar  # 해당 월의 일수를 계산하기 위해 추가

# ----------------- Configuration -----------------
# Base directory for all files(param, run.bat, hydroconstruct.exe). 경로가 바뀔 경우 이 값만 수정하면 됩니다.
base_path = r"H:\Dropbox\y2025\01_Atlantis\06_hydro\branches\s1"

# 파일 경로 설정
template_param_file = os.path.join(base_path, "param_2025.prm")   # param 파일
original_run_bat    = os.path.join(base_path, "run.bat")           # 원본 run.bat (참고용)
hydroconstruct_exe  = os.path.join(base_path, "hydroconstruct.exe")# 실행 파일

# geofile 및 llgeofile 파일명과 절대 경로 설정 (param 파일 내 변수로 사용)
#geofile_filename    = "version2_utm_relax.bgm"
#llgeofile_filename  = "version2_relax.bgm"
#geofile_path        = os.path.join(base_path, geofile_filename)
#llgeofile_path      = os.path.join(base_path, llgeofile_filename)

# --------------------------------------------------

# 처리할 연도
year = 2019

# 작업 디렉터리: 입력파일(trans, tempsalt 등)이 위치하는 폴더(연도별)
working_dir = os.path.join(base_path, str(year))

# 기준 날짜: 2019년 1월 1일 0시 (참고용)
global_ref = pd.to_datetime(f"{year}-01-01 00:00:00")

# ----------------- Main Loop -----------------
for month in range(1, 13):
    # 해당 월의 시작 시각 계산 (필요 시점 계산용)
    month_start = pd.to_datetime(f"{year}-{month:02d}-01 00:00:00")
    # tstart는 항상 0으로 고정, tstop은 해당 월의 일수로 설정
    tstart_val = 0
    tstop_val  = calendar.monthrange(year, month)[1]-1

    tstart_line = f"tstart {tstart_val}\n"
    tstop_line  = f"tstop {tstop_val}\n"

    # 입력 nc 파일 경로 (working_dir 기준)
    tempsalt_nc = os.path.join(working_dir, f"avs_{year}_{month:02d}.nc")
    trans_nc    = os.path.join(working_dir, f"trans_{year}_{month:02d}.nc")
    vtrans_nc   = os.path.join(working_dir, f"avs_{year}_{month:02d}.nc")
    
    # param 파일 내에 기록할 변수들
    tempsalt_line  = f"tempsalt0.name {tempsalt_nc}\n"
    trans_line     = f"trans0.name {trans_nc}\n"
    vtrans_line    = f"vtrans0.name {vtrans_nc}\n"
    reference_line = f"reference_year {year}\n"
#    geofile_line   = f"geofile {geofile_path}\n"
#    llgeofile_line = f"llgeofile {llgeofile_path}\n"

    # 템플릿 param 파일 읽기 및 수정 (필요 항목만 교체)
    with open(template_param_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("tempsalt0.name"):
            new_lines.append(tempsalt_line)
        elif stripped.startswith("vtrans0.name"):
            new_lines.append(vtrans_line)
        elif stripped.startswith("trans0.name"):
            new_lines.append(trans_line)
        elif stripped.startswith("reference_year"):
            new_lines.append(reference_line)
        elif stripped.startswith("tstart"):
            new_lines.append(tstart_line)
        elif stripped.startswith("tstop"):
            new_lines.append(tstop_line)
       # elif stripped.startswith("geofile"):
       #     new_lines.append(geofile_line)
       # elif stripped.startswith("llgeofile"):
       #     new_lines.append(llgeofile_line)
        else:
            new_lines.append(line)

    # 수정된 param 파일 내용 저장 (덮어쓰기)
    with open(template_param_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 임시 배치 파일(temp_run.bat) 생성 (working_dir 내)
    bat_content = (
        f'"{hydroconstruct_exe}" '
        f'-f flow_{year}_{month:02d}.txt '
        f'-s salt_{year}_{month:02d}.txt '
        f'-t temp_{year}_{month:02d}.txt '
        f'-r "{template_param_file}"\n'
    )
    temp_run_bat = os.path.join(working_dir, "temp_run.bat")
    with open(temp_run_bat, "w", encoding="utf-8") as f:
        f.write(bat_content)

    print(f"[{year}-{month:02d}] 임시 배치 파일 생성 완료: {temp_run_bat}")
    print(f"    내용: {bat_content.strip()}")

    # 임시 배치 파일 실행
    result = subprocess.run(temp_run_bat, shell=True, cwd=working_dir)
    print(result.stdout)
    print(result.stderr)
      
    if result.returncode != 0:
        print(f"[{year}-{month:02d}] hydroconstruct.exe 실행 중 오류 발생!")
        os.remove(temp_run_bat)
        continue
    else:
        print(f"[{year}-{month:02d}] hydroconstruct.exe 실행 완료.")

    # 실행 후 임시 배치 파일 삭제
    os.remove(temp_run_bat)

print("모든 월별 작업이 완료되었습니다.")
