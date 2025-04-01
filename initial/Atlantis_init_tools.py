# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 14:03:58 2025

@author: Ukjae
"""
import os
import re
import numpy as np
import pandas as pd
from netCDF4 import Dataset

# ---------------------------------------------------------------------------
# make_map_data_init: BGM 파일과 누적 깊이(cum_depths) 벡터를 이용하여 각 상자의
# 지오메트리 정보를 계산 (MATLAB: makeMapDataInit.m)
# ---------------------------------------------------------------------------
def make_map_data_init(bgm_file, cum_depths):
    with open(bgm_file, 'r') as f:
        lines = f.readlines()
    
    numboxes = 0
    # BGM 파일에서 "nbox" 행을 찾아 상자 개수를 결정
    for line in lines:
        if line.strip().startswith("nbox"):
            parts = re.split(r'\s+', line.strip())
            try:
                numboxes = int(float(parts[1]))
            except:
                numboxes = 0
            break

    # 각 상자의 바닥 깊이 (botz)와 면적을 추출
    z = []
    area = []
    for i in range(numboxes):
        # botz 추출
        pattern_botz = f"box{i}.botz"
        botz_val = np.nan
        for line in lines:
            if pattern_botz in line:
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 2:
                    try:
                        botz_val = float(parts[1])
                    except:
                        botz_val = np.nan
                break
        z.append(botz_val)
        # area 추출
        pattern_area = f"box{i}.area"
        area_val = np.nan
        for line in lines:
            if pattern_area in line:
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 2:
                    try:
                        area_val = float(parts[1])
                    except:
                        area_val = np.nan
                break
        area.append(area_val)
    z = np.array(z)
    area = np.array(area)
    # R 코드에서 total_depth = -z
    total_depth = -z
    # 부피 계산 (섬의 경우 부호 반전)
    volume = total_depth * area
    is_island = total_depth <= 0.0
    volume[is_island] = -volume[is_island]
    
    # 각 상자에 대해 물층 수 계산
    max_layers = len(cum_depths) - 1
    numlayers = np.array([min(np.sum(td > np.array(cum_depths)), max_layers) for td in total_depth])
    
    # 각 상자에서 불완전한(최상위) 물층의 깊이 계산 (volume 계산에 필요)
    deepest_depth = []
    max_layer_depth = max(cum_depths)
    for td, nl in zip(total_depth, numlayers):
        if nl > 0:
            d = min(td, max_layer_depth) - cum_depths[int(nl)]
        else:
            d = 0.0
        deepest_depth.append(d)
    deepest_depth = np.array(deepest_depth)
    
    # 결과를 DataFrame에 저장
    box_data = pd.DataFrame({
        'boxid': np.arange(numboxes),
        'total_depth': total_depth,
        'area': area,
        'volume': volume,
        'numlayers': numlayers,
        'deepest_depth': deepest_depth,
        'is_island': is_island
    })
    return {'numboxes': numboxes, 'boxData': box_data, 'cumDepths': cum_depths}

# ---------------------------------------------------------------------------
# generate_vars_init: 그룹 CSV 파일과 Attribute Template를 이용하여 각 그룹의
# 생물학적 변수 정보를 생성 (MATLAB: generateVarsInit.m)
# ---------------------------------------------------------------------------
def generate_vars_init(grp_file, cum_depths, df_atts, ice_model=False):
    # 그룹 CSV 읽기
    df_grp = pd.read_csv(grp_file)
    # MATLAB에서는 'InvertType'이 있으면 'GroupType'으로 변경
    if 'InvertType' in df_grp.columns:
        df_grp = df_grp.rename(columns={'InvertType': 'GroupType'})
    df_grp['GroupType'] = df_grp['GroupType'].astype(str)
    # 숫자형 컬럼 변환
    for col in ['IsCover', 'NumCohorts', 'IsSiliconDep']:
        if col in df_grp.columns:
            df_grp[col] = pd.to_numeric(df_grp[col], errors='coerce')
    
    # 에피벤트로스 그룹 정의
    epiGrpsDef = ['SED_EP_FF', 'SED_EP_OTHER', 'EP_OTHER', 'MOB_EP_OTHER', 
                  'MICROPHTYBENTHOS', 'PHYTOBEN', 'SEAGRASS', 'CORAL']
    df_grp['isEpiGrp'] = df_grp['GroupType'].isin(epiGrpsDef)
    
    # cover 그룹 (IsCover == 1)
    # 다중 코호트 플래그
    df_grp['multiN'] = ((df_grp['IsCover'] == 1) & (df_grp['NumCohorts'] > 1)) | \
                       ((df_grp['GroupType'] == 'PWN') & (df_grp['NumCohorts'] > 1)) | \
                       ((df_grp['GroupType'] == 'CEP') & (df_grp['NumCohorts'] > 1))
    # needsNums 플래그: 특정 그룹에 대해
    srGrps = ['FISH', 'BIRD', 'SHARK', 'MAMMAL', 'REPTILE', 'FISH_INVERT']
    df_grp['needsNums'] = df_grp['GroupType'].isin(srGrps)
    # needsLight 플래그
    lightAdpnGrps = ['DINOFLAG', 'MICROPHTYBENTHOS', 'SM_PHY', 'MED_PHY', 'LG_PHY']
    df_grp['needsLight'] = df_grp['GroupType'].isin(lightAdpnGrps)
    
    # Invert 변수 (그룹이 needsNums가 False인 경우)
    Variables = []
    long_name = []
    att_index = []
    for idx, row in df_grp.iterrows():
        if not row['needsNums']:
            if not row['multiN']:
                Variables.append(f"{row['Name']}_N")
                target = f"{row['GroupType']}_N"
                indx = df_atts.index[df_atts['name'] == target]
                if len(indx) > 0:
                    indx_val = indx[0]
                    long_name.append(f"{row['Name']} {df_atts.loc[indx_val, 'long_name']}")
                else:
                    indx_val = -1
                    long_name.append(f"{row['Name']} N")
                att_index.append(indx_val)
            else:
                for j in range(int(row['NumCohorts'])):
                    Variables.append(f"{row['Name']}_N{j+1}")
                    target = f"{row['GroupType']}_N"
                    indx = df_atts.index[df_atts['name'] == target]
                    if len(indx) > 0:
                        indx_val = indx[0]
                        long_name.append(f"{row['Name']} cohort {j+1} {df_atts.loc[indx_val, 'long_name']}")
                    else:
                        indx_val = -1
                        long_name.append(f"{row['Name']} N{j+1}")
                    att_index.append(indx_val)
            if row['IsCover'] == 1:
                Variables.append(f"{row['Name']}_Cover")
                indx = df_atts.index[df_atts['name'] == 'Cover']
                if len(indx) > 0:
                    indx_val = indx[0]
                    long_name.append(f"Percent cover by {row['Name']}")
                else:
                    indx_val = -1
                    long_name.append(f"{row['Name']} Cover")
                att_index.append(indx_val)
            if row['IsSiliconDep'] == 1:
                Variables.append(f"{row['Name']}_S")
                # MATLAB 코드: 사용된 이름은 'Si3D'
                indx = df_atts.index[df_atts['name'] == 'Si3D']
                if len(indx) > 0:
                    indx_val = indx[0]
                    long_name.append(f"{row['Name']} Silicon")
                else:
                    indx_val = -1
                    long_name.append(f"{row['Name']} S")
                att_index.append(indx_val)
            if row['needsLight']:
                Variables.append(f"Light_Adaptn_{row['Code']}")
                indx = df_atts.index[df_atts['name'] == 'Light3D']
                if len(indx) > 0:
                    indx_val = indx[0]
                    long_name.append(f"Light adaption of {row['Name']}")
                else:
                    indx_val = -1
                    long_name.append(f"Light_{row['Name']}")
                att_index.append(indx_val)
    dfInvert = pd.DataFrame({
        'Variable': Variables,
        'long_name': long_name,
        'att_index': att_index
    })
    
    # Vertebrate 변수 (needsNums == True)
    Variables = []
    long_name = []
    att_index = []
    for idx, row in df_grp.iterrows():
        if row['needsNums']:
            Variables.append(f"{row['Name']}_N")
            target = f"{row['GroupType']}_N"
            indx = df_atts.index[df_atts['name'] == target]
            if len(indx) > 0:
                indx_val = indx[0]
                long_name.append(f"{row['Name']} {df_atts.loc[indx_val, 'long_name']}")
            else:
                indx_val = -1
                long_name.append(f"{row['Name']} N")
            att_index.append(indx_val)
            for j in range(int(row['NumCohorts'])):
                Variables.append(f"{row['Name']}{j+1}_Nums")
                indx = df_atts.index[df_atts['name'] == 'Nums3D']
                if len(indx) > 0:
                    indx_val = indx[0]
                    long_name.append(f"Numbers of {row['Name']} cohort {j+1}")
                else:
                    indx_val = -1
                    long_name.append(f"{row['Name']} Nums{j+1}")
                att_index.append(indx_val)
            for j in range(int(row['NumCohorts'])):
                Variables.append(f"{row['Name']}{j+1}_StructN")
                indx = df_atts.index[df_atts['name'] == 'StructN3D']
                if len(indx) > 0:
                    indx_val = indx[0]
                    long_name.append(f"Individual structural N for {row['Name']} cohort {j+1}")
                else:
                    indx_val = -1
                    long_name.append(f"{row['Name']} StructN{j+1}")
                att_index.append(indx_val)
            for j in range(int(row['NumCohorts'])):
                Variables.append(f"{row['Name']}{j+1}_ResN")
                indx = df_atts.index[df_atts['name'] == 'ResN3D']
                if len(indx) > 0:
                    indx_val = indx[0]
                    long_name.append(f"Individual reserve N for {row['Name']} cohort {j+1}")
                else:
                    indx_val = -1
                    long_name.append(f"{row['Name']} ResN{j+1}")
                att_index.append(indx_val)
    dfVert = pd.DataFrame({
        'Variable': Variables,
        'long_name': long_name,
        'att_index': att_index
    })
    dfreturn = pd.concat([dfInvert, dfVert], ignore_index=True)
    return dfreturn

# ---------------------------------------------------------------------------
# make_init_csv: 그룹 파일, BGM 파일, 누적 깊이 정보를 이용해 초기 조건 CSV 템플릿과 
# horizontal distribution CSV 템플릿을 생성 (MATLAB: makeInitCsv.m)
# ---------------------------------------------------------------------------
def make_init_csv(grp_file, bgm_file, cum_depths, csv_name, ice_model=False):
    # def.att.file 경로 (여기서는 현재 작업 폴더의 파일로 가정)
    def_att_file = "AttributeTemplate.csv"
    df_atts = pd.read_csv(def_att_file, header=0, dtype=str)
    
    # 만약 일부 값이 불리언 등으로 되어 있다면 문자열로 강제 변환
    df_atts['required'] = df_atts['required'].astype(str)
    
    numlayers = len(cum_depths) - 1
    layer_depth = [cum_depths[i+1] - cum_depths[i] for i in range(numlayers)]
    numsed = 1

    map_data = make_map_data_init(bgm_file, cum_depths)
    numboxes = map_data['numboxes']
    box_data = map_data['boxData']
    
    # ice_model이 True이면 필요한 변수의 required 플래그를 TRUE 문자열로 설정
    if ice_model:
        df_atts.loc[df_atts['name'].isin(['ice_dz', 'SED']), 'required'] = "TRUE"
    # required가 "TRUE"인 행 선택
    df_return = df_atts[df_atts['required'].str.upper() == "TRUE"].copy()
    
    # 그룹 관련 변수 추가
    grp_data = generate_vars_init(grp_file, cum_depths, df_atts, ice_model)
    df_return = pd.concat([df_return, grp_data], ignore_index=True)
    
    df_return.to_csv(f"{csv_name}_init.csv", index=False)
    
    # 사용자 지정 horizontal distribution을 위한 템플릿 생성
    if 'wc_hor_pattern' in df_return.columns:
        custom_vars = df_return.loc[df_return['wc_hor_pattern'].str.strip() == "custom", 'name'].tolist()
    else:
        custom_vars = []
    n_custom = len(custom_vars)
    ma_vals = np.zeros((n_custom, numboxes))
    df_custom = pd.DataFrame(ma_vals, columns=[f"box{i}" for i in range(numboxes)])
    df_custom.insert(0, "Variable", custom_vars)
    df_custom.to_csv(f"{csv_name}_horiz.csv", index=False)


# ---------------------------------------------------------------------------
# get_init_nc: NetCDF 파일의 초기 조건 값을 읽어 CSV 파일로 저장 (MATLAB: getInitNc.m)
# ---------------------------------------------------------------------------
def get_init_nc(nc_file, output_file):
    import numpy as np
    import pandas as pd
    from netCDF4 import Dataset

    nc = Dataset(nc_file, 'r')
    var_names_all = list(nc.variables.keys())
    # 'reef' 변수가 있다면 상자 수 추출, 없으면 다른 변수에서 추정
    if "reef" in nc.variables:
        reef_var = nc.variables["reef"][:]
        numboxes = int(max(reef_var.shape))
    else:
        dims = [nc.variables[v].shape for v in var_names_all if len(nc.variables[v].shape) > 0]
        numboxes = int(max([max(shape) for shape in dims]))
    
    m_data = []
    for var_name in var_names_all:
        data_all = nc.variables[var_name][:]
        # 데이터를 float 형으로 변환한 후 flatten
        data_flat = np.array(data_all, dtype=float).flatten()
        # 강제로 길이를 numboxes로 맞춤: 짧으면 np.nan 패딩, 길면 자름
        if len(data_flat) < numboxes:
            data_flat = np.pad(data_flat, (0, numboxes - len(data_flat)), constant_values=np.nan)
        else:
            data_flat = data_flat[:numboxes]
        m_data.append(data_flat)
    m_data = np.array(m_data)
    columns = ["Variable"] + [f"box{i}" for i in range(numboxes)]
    df_out = pd.DataFrame(m_data, index=var_names_all, columns=columns[1:])
    df_out.insert(0, "Variable", var_names_all)
    df_out.to_csv(output_file, index=False)
    nc.close()

# ---------------------------------------------------------------------------
# 예제 사용법
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 누적 깊이 벡터 (첫 값 0)
    cum_depths = [0, 10, 50, 200, 600, 1500, 3500]
    
    # 입력 파일 경로 (MATLAB 코드 예시와 유사)
    grp_file = "KOR_FGROUP2.csv"
    bgm_file = "version2_utm_relax.bgm"
    csv_name = "GBRtemplate"
    nc_file  = "GBRtemplate.nc"
    # vert_file은 선택사항 (없으면 None)
    vert_file = None
    
    # 초기 CSV 템플릿 생성
    make_init_csv(grp_file, bgm_file, cum_depths, csv_name, ice_model=True)
    
    # (여기서는 NetCDF 생성 함수는 별도로 작성하지 않았으므로, 필요시 추가 구현)
    
    # NetCDF에서 초기조건 CSV 추출
    get_init_nc(nc_file, "initial_conditions_output.csv")
