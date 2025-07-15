from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback
from typing import List, Optional
import uvicorn
import re
import math
from datetime import datetime, timedelta

app = FastAPI(title="純開源八字計算API", description="不依賴外部庫的八字命理系統", version="6.0.0")

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 天干地支對照表
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 六十甲子納音表
NAYIN = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "爐中火", "丁卯": "爐中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "劍鋒金", "癸酉": "劍鋒金", "甲戌": "山頭火", "乙亥": "山頭火",
    "丙子": "澗下水", "丁丑": "澗下水", "戊寅": "城頭土", "己卯": "城頭土",
    "庚辰": "白蠟金", "辛巳": "白蠟金", "壬午": "楊柳木", "癸未": "楊柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹靂火", "己丑": "霹靂火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "長流水", "癸巳": "長流水", "甲午": "砂中金", "乙未": "砂中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆燈火", "乙巳": "覆燈火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驛土", "己酉": "大驛土", "庚戌": "釵釧金", "辛亥": "釵釧金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "砂中土", "丁巳": "砂中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水"
}

# 十神對照表
SHI_SHEN_MAP = {
    "甲": {"甲": "比肩", "乙": "劫財", "丙": "食神", "丁": "傷官", "戊": "偏財", "己": "正財", "庚": "七殺", "辛": "正官", "壬": "偏印", "癸": "正印"},
    "乙": {"甲": "劫財", "乙": "比肩", "丙": "傷官", "丁": "食神", "戊": "正財", "己": "偏財", "庚": "正官", "辛": "七殺", "壬": "正印", "癸": "偏印"},
    "丙": {"甲": "偏印", "乙": "正印", "丙": "比肩", "丁": "劫財", "戊": "食神", "己": "傷官", "庚": "偏財", "辛": "正財", "壬": "七殺", "癸": "正官"},
    "丁": {"甲": "正印", "乙": "偏印", "丙": "劫財", "丁": "比肩", "戊": "傷官", "己": "食神", "庚": "正財", "辛": "偏財", "壬": "正官", "癸": "七殺"},
    "戊": {"甲": "七殺", "乙": "正官", "丙": "偏印", "丁": "正印", "戊": "比肩", "己": "劫財", "庚": "食神", "辛": "傷官", "壬": "偏財", "癸": "正財"},
    "己": {"甲": "正官", "乙": "七殺", "丙": "正印", "丁": "偏印", "戊": "劫財", "己": "比肩", "庚": "傷官", "辛": "食神", "壬": "正財", "癸": "偏財"},
    "庚": {"甲": "偏財", "乙": "正財", "丙": "七殺", "丁": "正官", "戊": "偏印", "己": "正印", "庚": "比肩", "辛": "劫財", "壬": "食神", "癸": "傷官"},
    "辛": {"甲": "正財", "乙": "偏財", "丙": "正官", "丁": "七殺", "戊": "正印", "己": "偏印", "庚": "劫財", "辛": "比肩", "壬": "傷官", "癸": "食神"},
    "壬": {"甲": "食神", "乙": "傷官", "丙": "偏財", "丁": "正財", "戊": "七殺", "己": "正官", "庚": "偏印", "辛": "正印", "壬": "比肩", "癸": "劫財"},
    "癸": {"甲": "傷官", "乙": "食神", "丙": "正財", "丁": "偏財", "戊": "正官", "己": "七殺", "庚": "正印", "辛": "偏印", "壬": "劫財", "癸": "比肩"}
}

# 地支藏干表
DIZHI_CANGAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"], "午": ["丁", "己"], "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"], "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"]
}

# 五行對照表
WU_XING = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", 
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"
}

class ChartRequest(BaseModel):
    date: str
    time: str
    lat: float
    lon: float
    tz: float = 8.0

def parse_date_string(date_str):
    """解析各種日期格式"""
    try:
        clean_date = re.sub(r'[^0-9]', '', date_str)
        
        if len(clean_date) == 8:
            year = int(clean_date[:4])
            month = int(clean_date[4:6])
            day = int(clean_date[6:8])
            return year, month, day
        
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                if len(parts[0]) == 4:
                    return int(parts[0]), int(parts[1]), int(parts[2])
                else:
                    return int(parts[2]), int(parts[0]), int(parts[1])
        
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                return int(parts[0]), int(parts[1]), int(parts[2])
        
        raise ValueError(f"無法解析日期格式: {date_str}")
        
    except Exception as e:
        raise ValueError(f"日期解析錯誤: {str(e)}")

def parse_time_string(time_str):
    """解析時間格式"""
    try:
        clean_time = time_str.strip().replace(' ', '')
        
        if ':' in clean_time:
            parts = clean_time.split(':')
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return hour, minute
        
        if len(clean_time) == 4 and clean_time.isdigit():
            hour = int(clean_time[:2])
            minute = int(clean_time[2:4])
            return hour, minute
        
        if len(clean_time) <= 2 and clean_time.isdigit():
            hour = int(clean_time)
            minute = 0
            return hour, minute
        
        return 12, 0
        
    except Exception as e:
        return 12, 0

def get_ganzhi_from_number(num, is_gan=True):
    """根據數字獲取天干或地支"""
    if is_gan:
        return TIAN_GAN[num % 10]
    else:
        return DI_ZHI[num % 12]

def get_year_ganzhi(year):
    """計算年柱天干地支"""
    # 以甲子年(1984)為基準
    gan_index = (year - 1984) % 10
    zhi_index = (year - 1984) % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_month_ganzhi(year, month):
    """計算月柱天干地支"""
    # 地支固定：寅月(正月)開始
    month_zhi = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
    zhi = month_zhi[month - 1]
    
    # 天干根據年干推算
    year_gan = get_year_ganzhi(year)[0]
    year_gan_index = TIAN_GAN.index(year_gan)
    
    # 月干公式：甲己之年丙作首
    month_gan_base = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]  # 對應甲乙丙丁戊己庚辛壬癸年的正月天干
    gan_index = (month_gan_base[year_gan_index] + month - 1) % 10
    gan = TIAN_GAN[gan_index]
    
    return gan, zhi

def get_day_ganzhi(year, month, day):
    """計算日柱天干地支"""
    # 使用簡化的公式計算日柱
    # 以1900年1月1日為甲戌日作為基準
    base_date = datetime(1900, 1, 1)
    target_date = datetime(year, month, day)
    days_diff = (target_date - base_date).days
    
    # 1900年1月1日是甲戌日，甲=0，戌=10
    gan_index = (0 + days_diff) % 10
    zhi_index = (10 + days_diff) % 12
    
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_hour_ganzhi(day_gan, hour):
    """計算時柱天干地支"""
    # 時辰地支
    hour_zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    zhi_index = ((hour + 1) // 2) % 12
    zhi = hour_zhi[zhi_index]
    
    # 時干根據日干推算
    day_gan_index = TIAN_GAN.index(day_gan)
    hour_gan_base = [0, 2, 4, 6, 8, 0, 2, 4, 6, 8]  # 甲己日子時起甲子
    gan_index = (hour_gan_base[day_gan_index] + zhi_index) % 10
    gan = TIAN_GAN[gan_index]
    
    return gan, zhi

def calculate_shi_shen(day_gan, target_gan):
    """計算十神"""
    return SHI_SHEN_MAP[day_gan][target_gan]

def get_nayin(gan, zhi):
    """獲取納音"""
    ganzhi = gan + zhi
    return NAYIN.get(ganzhi, "未知")

def analyze_wu_xing_strength(bazi_pillars):
    """五行強弱分析"""
    wu_xing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    
    # 計算天干五行
    for pillar in bazi_pillars:
        gan = pillar["天干"]
        zhi = pillar["地支"]
        
        # 天干五行
        wu_xing_count[WU_XING[gan]] += 2
        
        # 地支藏干五行
        cangan_list = DIZHI_CANGAN[zhi]
        for cangan in cangan_list:
            wu_xing_count[WU_XING[cangan]] += 1
    
    return wu_xing_count

def calculate_pure_bazi(birth_date, birth_time, latitude=None, longitude=None):
    """純開源八字計算"""
    try:
        year, month, day = parse_date_string(birth_date)
        hour, minute = parse_time_string(birth_time)
        
        # 驗證日期時間
        if not (1 <= month <= 12):
            month = 1
        if not (1 <= day <= 31):
            day = 1
        if not (0 <= hour <= 23):
            hour = 12
        if not (0 <= minute <= 59):
            minute = 0
        
        # 計算四柱
        year_gan, year_zhi = get_year_ganzhi(year)
        month_gan, month_zhi = get_month_ganzhi(year, month)
        day_gan, day_zhi = get_day_ganzhi(year, month, day)
        hour_gan, hour_zhi = get_hour_ganzhi(day_gan, hour)
        
        # 組成八字
        bazi_pillars = [
            {"天干": year_gan, "地支": year_zhi, "柱名": "年柱"},
            {"天干": month_gan, "地支": month_zhi, "柱名": "月柱"},
            {"天干": day_gan, "地支": day_zhi, "柱名": "日柱"},
            {"天干": hour_gan, "地支": hour_zhi, "柱名": "時柱"}
        ]
        
        # 計算納音
        for pillar in bazi_pillars:
            pillar["納音"] = get_nayin(pillar["天干"], pillar["地支"])
        
        # 計算十神
        shi_shen_info = {}
        for pillar in bazi_pillars:
            gan = pillar["天干"]
            if gan != day_gan:  # 不計算日干自己
                shi_shen_info[f"{pillar['柱名']}干"] = calculate_shi_shen(day_gan, gan)
            
            # 地支藏干十神
            cangan_list = DIZHI_CANGAN[pillar["地支"]]
            for i, cangan in enumerate(cangan_list):
                if cangan != day_gan:
                    shi_shen_info[f"{pillar['柱名']}支藏干{i+1}"] = calculate_shi_shen(day_gan, cangan)
        
        # 五行分析
        wu_xing_analysis = analyze_wu_xing_strength(bazi_pillars)
        
        # 日主五行
        day_wu_xing = WU_XING[day_gan]
        
        # 基本格局判斷（簡化）
        day_strength = wu_xing_analysis[day_wu_xing]
        total_strength = sum(wu_xing_analysis.values())
        strength_ratio = day_strength / total_strength
        
        if strength_ratio > 0.3:
            body_strength = "身強"
            yong_shen = get_weak_elements(wu_xing_analysis)
        else:
            body_strength = "身弱"
            yong_shen = get_strong_elements(wu_xing_analysis, day_wu_xing)
        
        # 大運計算（簡化版）
        da_yun = calculate_da_yun(year_gan, month_gan, month_zhi)
        
        return {
            "八字命盤": {
                "年柱": {"天干": year_gan, "地支": year_zhi, "納音": get_nayin(year_gan, year_zhi)},
                "月柱": {"天干": month_gan, "地支": month_zhi, "納音": get_nayin(month_gan, month_zhi)},
                "日柱": {"天干": day_gan, "地支": day_zhi, "納音": get_nayin(day_gan, day_zhi)},
                "時柱": {"天干": hour_gan, "地支": hour_zhi, "納音": get_nayin(hour_gan, hour_zhi)}
            },
            "日主": day_gan,
            "日主五行": day_wu_xing,
            "十神分析": shi_shen_info,
            "五行分析": wu_xing_analysis,
            "身強身弱": body_strength,
            "用神建議": yong_shen,
            "大運": da_yun,
            "基本信息": {
                "公曆": f"{year}年{month}月{day}日 {hour}時{minute}分",
                "計算方式": "純開源算法"
            }
        }
        
    except Exception as e:
        raise Exception(f"八字計算錯誤: {str(e)}")

def get_weak_elements(wu_xing_analysis):
    """獲取較弱的五行作為用神"""
    sorted_elements = sorted(wu_xing_analysis.items(), key=lambda x: x[1])
    return [elem[0] for elem in sorted_elements[:2]]

def get_strong_elements(wu_xing_analysis, day_wu_xing):
    """獲取能扶助日主的五行"""
    helper_elements = {
        "木": ["水", "木"], "火": ["木", "火"], "土": ["火", "土"],
        "金": ["土", "金"], "水": ["金", "水"]
    }
    return helper_elements.get(day_wu_xing, ["需詳細分析"])

def calculate_da_yun(year_gan, month_gan, month_zhi):
    """計算大運（簡化版）"""
    da_yun_list = []
    
    # 從月柱開始推算大運
    month_gan_index = TIAN_GAN.index(month_gan)
    month_zhi_index = DI_ZHI.index(month_zhi)
    
    for i in range(8):  # 計算8步大運
        da_yun_gan = TIAN_GAN[(month_gan_index + i + 1) % 10]
        da_yun_zhi = DI_ZHI[(month_zhi_index + i + 1) % 12]
        
        da_yun_list.append({
            "大運": f"{da_yun_gan}{da_yun_zhi}",
            "起運年齡": 3 + i * 10,  # 簡化：3歲起運，每10年一步
            "結束年齡": 12 + i * 10,
            "納音": get_nayin(da_yun_gan, da_yun_zhi)
        })
    
    return da_yun_list

@app.get("/")
def read_root():
    return {
        "message": "純開源八字計算API", 
        "version": "6.0.0",
        "系統狀態": "完全獨立，無外部依賴",
        "支援功能": [
            "四柱八字排盤",
            "納音五行", 
            "十神分析",
            "五行強弱",
            "大運計算",
            "身強身弱判斷"
        ]
    }

@app.post("/bazi")
def analyze_pure_bazi(req: ChartRequest):
    """純開源八字分析"""
    try:
        clean_date = re.sub(r'[^0-9]', '', req.date)
        
        if len(clean_date) != 8:
            try:
                if '/' in req.date:
                    parts = req.date.split('/')
                    if len(parts) == 3:
                        if len(parts[0]) == 4:
                            clean_date = f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"
                        else:
                            clean_date = f"{parts[2]}{parts[0].zfill(2)}{parts[1].zfill(2)}"
                elif '-' in req.date:
                    parts = req.date.split('-')
                    if len(parts) == 3:
                        clean_date = f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"
            except:
                clean_date = "20000101"
        
        # 純開源八字計算
        bazi_data = calculate_pure_bazi(clean_date, req.time, req.lat, req.lon)
        
        return {
            "status": "success",
            "calculation_method": "純開源八字算法",
            "bazi_chart": bazi_data
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "pure-bazi-calculator",
        "dependencies": "無外部依賴",
        "version": "6.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
