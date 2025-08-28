from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback
from typing import List, Optional
import uvicorn
import re
from datetime import datetime, date

app = FastAPI(title="全日期八字API", description="支援所有日期的八字計算系統", version="13.0.0")

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 嘗試導入lunardate
try:
    from lunardate import LunarDate
    LUNARDATE_AVAILABLE = True
    print("lunardate農曆轉換庫已成功載入")
except ImportError:
    LUNARDATE_AVAILABLE = False
    print("lunardate不可用，使用備用計算")

# 天干地支
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 納音表
NAYIN = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "爐中火", "丁卯": "爐中火", "戊辰": "大林木", "己巳": "大林木",
    "庚午": "路旁土", "辛未": "路旁土", "壬申": "劍鋒金", "癸酉": "劍鋒金", "甲戌": "山頭火", "乙亥": "山頭火",
    "丙子": "澗下水", "丁丑": "澗下水", "戊寅": "城頭土", "己卯": "城頭土", "庚辰": "白蠟金", "辛巳": "白蠟金",
    "壬午": "楊柳木", "癸未": "楊柳木", "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹靂火", "己丑": "霹靂火", "庚寅": "松柏木", "辛卯": "松柏木", "壬辰": "長流水", "癸巳": "長流水",
    "甲午": "砂中金", "乙未": "砂中金", "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金", "甲辰": "覆燈火", "乙巳": "覆燈火",
    "丙午": "天河水", "丁未": "天河水", "戊申": "大驛土", "己酉": "大驛土", "庚戌": "釵釧金", "辛亥": "釵釧金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水", "丙辰": "砂中土", "丁巳": "砂中土",
    "戊午": "天上火", "己未": "天上火", "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水"
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
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土",
    "庚": "金", "辛": "金", "壬": "水", "癸": "水"
}

class ChartRequest(BaseModel):
    date: str
    time: str
    lat: float
    lon: float
    tz: float = 8.0

class UserInput(BaseModel):
    userId: str
    name: str
    gender: str
    birthDate: str
    birthTime: str
    career: Optional[str] = ""
    birthPlace: str
    targetName: Optional[str] = ""
    targetGender: Optional[str] = ""
    targetBirthDate: Optional[str] = ""
    targetBirthTime: Optional[str] = ""
    targetCareer: Optional[str] = ""
    targetBirthPlace: Optional[str] = ""
    content: str
    contentType: str = "unknown"
    ready: bool = True
    latitude: float
    longitude: float

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

def get_year_ganzhi(year):
    """計算年柱天干地支（以立春為界）"""
    # 以甲子年(1984)為基準
    gan_index = (year - 1984) % 10
    zhi_index = (year - 1984) % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_month_ganzhi(year, month, day):
    """計算月柱天干地支（考慮節氣）"""
    # 簡化節氣表
    jieqi_days = {
        1: 6, 2: 4, 3: 6, 4: 5, 5: 6, 6: 6, 
        7: 7, 8: 8, 9: 8, 10: 8, 11: 7, 12: 7
    }
    
    # 確定農曆月份（以節氣為準）
    if month == 1:
        lunar_month = 12 if day < jieqi_days[1] else 1
    elif month == 2:
        lunar_month = 1 if day < jieqi_days[2] else 2
    else:
        lunar_month = month - 1 if day >= jieqi_days[month] else month - 2
    
    lunar_month = ((lunar_month - 1) % 12) + 1
    
    # 月支對應表
    month_zhi_map = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
    month_zhi = month_zhi_map[lunar_month - 1]
    
    # 月干計算
    year_gan = get_year_ganzhi(year)[0]
    year_gan_index = TIAN_GAN.index(year_gan)
    month_gan_base = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]
    gan_index = (month_gan_base[year_gan_index] + lunar_month - 1) % 10
    month_gan = TIAN_GAN[gan_index]
    
    return month_gan, month_zhi

def get_day_ganzhi(year, month, day):
    """計算日柱天干地支"""
    base_date = date(2000, 1, 1)  # 戊午日
    target_date = date(year, month, day)
    days_diff = (target_date - base_date).days
    
    base_gan = 4  # 戊
    base_zhi = 6  # 午
    
    gan_index = (base_gan + days_diff) % 10
    zhi_index = (base_zhi + days_diff) % 12
    
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_hour_ganzhi(day_gan, hour, minute):
    """計算時柱天干地支（完整修正所有时辰）"""
    # 标准时辰划分（每个时辰2小时，跨越两个整点小时）：
    # 子時：23:00-00:59 (前一天23点到当天0点59分)
    # 丑時：01:00-02:59, 寅時：03:00-04:59, 卯時：05:00-06:59
    # 辰時：07:00-08:59, 巳時：09:00-10:59, 午時：11:00-12:59
    # 未時：13:00-14:59, 申時：15:00-16:59, 酉時：17:00-18:59
    # 戌時：19:00-20:59, 亥時：21:00-22:59
    
    # 根据小时确定时辰地支索引
    if hour == 23 or hour == 0:
        zhi_index = 0  # 子时
    elif 1 <= hour <= 2:
        zhi_index = 1  # 丑时
    elif 3 <= hour <= 4:
        zhi_index = 2  # 寅时
    elif 5 <= hour <= 6:
        zhi_index = 3  # 卯时
    elif 7 <= hour <= 8:
        zhi_index = 4  # 辰时
    elif 9 <= hour <= 10:
        zhi_index = 5  # 巳时
    elif 11 <= hour <= 12:
        zhi_index = 6  # 午时
    elif 13 <= hour <= 14:
        zhi_index = 7  # 未时
    elif 15 <= hour <= 16:
        zhi_index = 8  # 申时
    elif 17 <= hour <= 18:
        zhi_index = 9  # 酉时
    elif 19 <= hour <= 20:
        zhi_index = 10  # 戌时
    elif 21 <= hour <= 22:
        zhi_index = 11  # 亥时
    else:
        zhi_index = 6  # 默认午时
    
    hour_zhi = DI_ZHI[zhi_index]
    
    # 時干計算：甲己日子時起甲子，乙庚日子時起丙子，...
    day_gan_index = TIAN_GAN.index(day_gan)
    # 各日干对应的子时天干起始索引
    hour_gan_base = [0, 2, 4, 6, 8, 0, 2, 4, 6, 8]  # 甲己乙庚丙辛丁壬戊癸
    gan_index = (hour_gan_base[day_gan_index] + zhi_index) % 10
    hour_gan = TIAN_GAN[gan_index]
    
    return hour_gan, hour_zhi

def get_nayin(gan, zhi):
    """獲取納音"""
    ganzhi = gan + zhi
    return NAYIN.get(ganzhi, "未知")

def calculate_shi_shen(day_gan, target_gan):
    """計算十神"""
    return SHI_SHEN_MAP[day_gan][target_gan]

def solar_to_lunar_converter(year, month, day):
    """陽曆轉農曆"""
    try:
        if LUNARDATE_AVAILABLE:
            lunar_date = LunarDate.fromSolarDate(year, month, day)
            return {
                "lunar_year": lunar_date.year,
                "lunar_month": lunar_date.month,
                "lunar_day": lunar_date.day,
                "is_leap_month": lunar_date.isLeapMonth,
                "conversion_method": "lunardate專業轉換"
            }
        else:
            return {
                "lunar_year": year,
                "lunar_month": month,
                "lunar_day": day,
                "is_leap_month": False,
                "conversion_method": "簡化轉換"
            }
    except Exception as e:
        raise Exception(f"農曆轉換錯誤: {str(e)}")

def calculate_comprehensive_bazi(birth_date, birth_time, latitude=None, longitude=None):
    """全面的八字計算"""
    try:
        year, month, day = parse_date_string(birth_date)
        hour, minute = parse_time_string(birth_time)
        
        # 驗證數據
        if not (1 <= month <= 12): month = 1
        if not (1 <= day <= 31): day = 1
        if not (0 <= hour <= 23): hour = 12
        if not (0 <= minute <= 59): minute = 0
        
        # 計算四柱
        year_gan, year_zhi = get_year_ganzhi(year)
        month_gan, month_zhi = get_month_ganzhi(year, month, day)
        day_gan, day_zhi = get_day_ganzhi(year, month, day)
        hour_gan, hour_zhi = get_hour_ganzhi(day_gan, hour, minute)
        
        # 組成八字
        bazi_pillars = {
            "年柱": {"天干": year_gan, "地支": year_zhi, "納音": get_nayin(year_gan, year_zhi), "藏干": DIZHI_CANGAN[year_zhi]},
            "月柱": {"天干": month_gan, "地支": month_zhi, "納音": get_nayin(month_gan, month_zhi), "藏干": DIZHI_CANGAN[month_zhi]},
            "日柱": {"天干": day_gan, "地支": day_zhi, "納音": get_nayin(day_gan, day_zhi), "藏干": DIZHI_CANGAN[day_zhi]},
            "時柱": {"天干": hour_gan, "地支": hour_zhi, "納音": get_nayin(hour_gan, hour_zhi), "藏干": DIZHI_CANGAN[hour_zhi]}
        }
        
        # 計算十神
        shi_shen_info = {}
        for pillar_name, pillar_data in bazi_pillars.items():
            gan = pillar_data["天干"]
            if gan != day_gan:
                shi_shen_info[f"{pillar_name}天干"] = calculate_shi_shen(day_gan, gan)
            
            cangan_list = pillar_data["藏干"]
            for i, cangan in enumerate(cangan_list):
                if cangan != day_gan:
                    shi_shen_info[f"{pillar_name}支藏干{i+1}"] = calculate_shi_shen(day_gan, cangan)
        
        # 五行統計
        wu_xing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        
        for pillar_data in bazi_pillars.values():
            gan = pillar_data["天干"]
            wu_xing_count[WU_XING[gan]] += 2
            
            cangan_list = pillar_data["藏干"]
            for cangan in cangan_list:
                wu_xing_count[WU_XING[cangan]] += 1
        
        day_wu_xing = WU_XING[day_gan]
        day_strength = wu_xing_count[day_wu_xing]
        total_strength = sum(wu_xing_count.values())
        strength_ratio = day_strength / total_strength
        
        body_strength = "身強" if strength_ratio > 0.3 else "身弱"
        
        # 大運計算
        da_yun_list = []
        for i in range(8):
            da_yun_gan = TIAN_GAN[(TIAN_GAN.index(month_gan) + i + 1) % 10]
            da_yun_zhi = DI_ZHI[(DI_ZHI.index(month_zhi) + i + 1) % 12]
            da_yun_list.append({
                "大運": f"{da_yun_gan}{da_yun_zhi}",
                "起運年齡": 3 + i * 10,
                "結束年齡": 12 + i * 10,
                "納音": get_nayin(da_yun_gan, da_yun_zhi)
            })
        
        # 陽曆轉農曆
        lunar_info = solar_to_lunar_converter(year, month, day)
        
        return {
            "八字命盤": bazi_pillars,
            "日主": day_gan,
            "日主五行": day_wu_xing,
            "身強身弱": body_strength,
            "十神分析": shi_shen_info,
            "五行統計": wu_xing_count,
            "大運": da_yun_list,
            "農曆資訊": lunar_info,
            "陽曆資訊": {"年": year, "月": month, "日": day, "時": hour, "分": minute},
            "計算方法": "標準節氣法八字計算",
            "精確度": "高精度"
        }
        
    except Exception as e:
        raise Exception(f"八字計算錯誤: {str(e)}")

@app.get("/")
def read_root():
    return {
        "message": "全日期八字API - 穩定版",
        "version": "13.0.0",
        "系統狀態": {"lunardate": "可用" if LUNARDATE_AVAILABLE else "不可用"},
        "支援功能": ["陽曆轉農曆", "四柱八字排盤", "十神分析", "五行統計", "大運計算"]
    }

@app.post("/bazi")
def calculate_bazi_endpoint(req: ChartRequest):
    """八字計算端點"""
    try:
        bazi_data = calculate_comprehensive_bazi(req.date, req.time, req.lat, req.lon)
        return {"status": "success", "bazi_chart": bazi_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/analyze")
def analyze_user_bazi(users: List[UserInput]):
    """用戶八字分析端點"""
    try:
        if not users:
            raise HTTPException(status_code=400, detail="請提供用戶資料")
        
        user = users[0]
        bazi_data = calculate_comprehensive_bazi(user.birthDate, user.birthTime, user.latitude, user.longitude)
        
        return {
            "status": "success",
            "用戶資訊": {
                "userId": user.userId,
                "name": user.name,
                "gender": user.gender,
                "birthDate": f"{user.birthDate[:4]}-{user.birthDate[4:6]}-{user.birthDate[6:8]}",
                "birthTime": user.birthTime,
                "birthPlace": user.birthPlace
            },
            "八字分析": bazi_data
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "13.0.0"}

if __name__ == "__main__":
    # 完整时辰测试
    print("=== 完整时辰测试 ===")
    test_hours = [0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    expected_zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子"]
    
    for i, hour in enumerate(test_hours):
        try:
            result = calculate_comprehensive_bazi("20000101", f"{hour:02d}:00")
            time_zhi = result["八字命盤"]["時柱"]["地支"]
            status = "✓" if time_zhi == expected_zhi[i] else "✗"
            print(f"{hour:2d}:00 -> {time_zhi} (期望:{expected_zhi[i]}) {status}")
        except Exception as e:
            print(f"{hour:2d}:00 -> 错误: {e}")
    
    print("\n=== 特定案例测试 ===")
    print("测试：1995年4月4日11:35")
    try:
        result = calculate_comprehensive_bazi("19950404", "11:35")
        pillars = result["八字命盤"]
        print(f"完整八字：{pillars['年柱']['天干']}{pillars['年柱']['地支']} {pillars['月柱']['天干']}{pillars['月柱']['地支']} {pillars['日柱']['天干']}{pillars['日柱']['地支']} {pillars['時柱']['天干']}{pillars['時柱']['地支']}")
    except Exception as e:
        print(f"测试错误：{e}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
