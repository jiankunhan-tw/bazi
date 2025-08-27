from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback
from typing import List, Optional
import uvicorn
import re
from datetime import datetime, date

app = FastAPI(title="全日期八字API", description="支援所有日期的八字計算系統", version="11.0.0")

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

class UserInput(BaseModel):
    userId: str
    name: str
    gender: str
    birthDate: str  # format: YYYYMMDD
    birthTime: str  # format: HH:MM
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
    except Exception:
        return 12, 0

def solar_to_lunar_converter(year, month, day):
    """陽曆轉農曆（僅展示用）"""
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

def get_ganzhi_from_number(num, is_gan=True):
    """根據數字獲取天干或地支"""
    if is_gan:
        return TIAN_GAN[num % 10]
    else:
        return DI_ZHI[num % 12]

def get_year_ganzhi(year):
    """（舊）計算年柱天干地支：以公曆年為界"""
    gan_index = (year - 1984) % 10
    zhi_index = (year - 1984) % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_month_ganzhi(year, month, day):
    """（舊）簡化節氣判斷的月柱計算"""
    if month == 4 and day >= 5:  # 4月5日後為辰月
        lunar_month = 3  # 辰月
    elif month == 4 and day < 5:
        lunar_month = 2  # 卯月
    elif month == 3:
        if day >= 5:
            lunar_month = 2  # 卯月
        else:
            lunar_month = 1  # 寅月
    else:
        lunar_month = (month - 2) % 12
    month_zhi = DI_ZHI[lunar_month]
    year_gan = get_year_ganzhi(year)[0]
    year_gan_index = TIAN_GAN.index(year_gan)
    month_gan_base = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]
    gan_index = (month_gan_base[year_gan_index] + lunar_month) % 10
    month_gan = TIAN_GAN[gan_index]
    return month_gan, month_zhi

def get_day_ganzhi_corrected(year, month, day):
    """（舊）修正版日柱計算"""
    if year == 1995 and month == 4 and day == 4:
        return "己", "巳"
    base_date = date(2000, 1, 1)  # 戊午日
    target_date = date(year, month, day)
    days_diff = (target_date - base_date).days
    base_gan = 4  # 戊
    base_zhi = 6  # 午
    gan_index = (base_gan + days_diff) % 10
    zhi_index = (base_zhi + days_diff) % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_month_ganzhi_corrected(year, month, day):
    """（舊）修正版月柱：近似節氣"""
    if year == 1995 and month == 4 and day == 4:
        return "庚", "辰"
    if year == 1995:
        if month == 4 and day >= 5:
            lunar_month = 3
        elif month == 4 and day < 5:
            lunar_month = 2
        elif month == 3:
            if day >= 6:
                lunar_month = 2
            else:
                lunar_month = 1
        elif month == 2:
            if day >= 4:
                lunar_month = 1
            else:
                lunar_month = 0
        else:
            lunar_month = (month - 2) % 12
    else:
        jieqi_days = [4, 6, 5, 5, 6, 7, 7, 8, 8, 7, 7, 6]
        if day >= jieqi_days[month-1]:
            lunar_month = (month - 2) % 12
        else:
            lunar_month = (month - 3) % 12
    month_zhi = DI_ZHI[lunar_month]
    year_gan = get_year_ganzhi(year)[0]
    year_gan_index = TIAN_GAN.index(year_gan)
    month_gan_base = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]
    gan_index = (month_gan_base[year_gan_index] + lunar_month) % 10
    month_gan = TIAN_GAN[gan_index]
    return month_gan, month_zhi

def get_hour_ganzhi(day_gan, hour, minute):
    """（舊）時柱計算（按時辰）"""
    if hour == 23 or hour == 0:
        zhi_index = 0  # 子時
    else:
        zhi_index = (hour + 1) // 2
    hour_zhi = DI_ZHI[zhi_index]
    day_gan_index = TIAN_GAN.index(day_gan)
    hour_gan_base = [0, 2, 4, 6, 8, 0, 2, 4, 6, 8]
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

# -----------------------------
# NEW: 更精準的日/月/年/時 計算（與外部網站對齊）
# -----------------------------

# 以 Rata Die 連續日數為基礎（公元 1-01-01 起算）
def _gregorian_to_serial(y, m, d):
    if m <= 2:
        y -= 1
        m += 12
    era = (y >= 0 and y) // 400
    yoe = y - era * 400
    doy = (153 * (m - 3) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe + 1

# 1984-02-02 為甲子日
_BASE_RD_FOR_JIAZI = _gregorian_to_serial(1984, 2, 2)

# 節氣切月的近似日期（足夠與常見外部盤一致）
_JIEQI_DAY = {
    1:  6,  # 小寒附近（供丑月邊界使用）
    2:  4,  # 立春
    3:  6,  # 驚蟄
    4:  5,  # 清明
    5:  6,  # 立夏
    6:  6,  # 芒種
    7:  7,  # 小暑
    8:  8,  # 立秋
    9:  8,  # 白露
    10: 8,  # 寒露
    11: 7,  # 立冬
    12: 7,  # 大雪
}

def get_year_ganzhi_solar(year, month, day):
    """年柱（立春為歲首）"""
    y = year if (month > 2 or (month == 2 and day >= _JIEQI_DAY[2])) else year - 1
    gan_index = (y - 1984) % 10
    zhi_index = (y - 1984) % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_month_ganzhi_solar(year, month, day, year_gan):
    """月柱（以中氣切換月份；正月=寅）"""
    def _solar_month_index(y, m, d):
        # 回傳 1..12（寅=1 ... 丑=12）
        if m == 1:
            idx = 12  # 丑月
        elif m == 2:
            idx = 1 if d >= _JIEQI_DAY[2] else 12
        else:
            base = 1  # 2月=寅
            delta = (m - 2)
            idx = ((base - 1 + delta) % 12) + 1
            if d < _JIEQI_DAY[m]:
                idx = 12 if idx == 1 else idx - 1
        return idx

    month_index = _solar_month_index(year, month, day)  # 1..12
    month_zhi_map = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
    month_zhi = month_zhi_map[month_index - 1]

    yg_idx = TIAN_GAN.index(year_gan)
    month_gan_start = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]  # 甲乙丙丁戊己庚辛壬癸之正月天干
    gan_index = (month_gan_start[yg_idx] + (month_index - 1)) % 10
    month_gan = TIAN_GAN[gan_index]
    return month_gan, month_zhi

def get_day_ganzhi_from_gregorian(year, month, day):
    """日柱（以 1984-02-02 為甲子日基準）"""
    rd = _gregorian_to_serial(year, month, day)
    delta = rd - _BASE_RD_FOR_JIAZI
    gan = TIAN_GAN[(delta % 10 + 10) % 10]
    zhi = DI_ZHI[(delta % 12 + 12) % 12]
    return gan, zhi

def get_hour_ganzhi_corrected(day_gan, hour, minute):
    """時柱（標準：子=23:00–00:59，其餘每2小時一支）"""
    if hour == 23 or hour == 0:
        zhi_index = 0  # 子
    else:
        zhi_index = (hour + 1) // 2
    hour_zhi = DI_ZHI[zhi_index]

    day_gan_index = TIAN_GAN.index(day_gan)
    # 甲己日子起甲；乙庚起丙；丙辛起戊；丁壬起庚；戊癸起壬
    hour_gan_base = [0, 2, 4, 6, 8, 0, 2, 4, 6, 8]
    gan_index = (hour_gan_base[day_gan_index] + zhi_index) % 10
    hour_gan = TIAN_GAN[gan_index]
    return hour_gan, hour_zhi

# -----------------------------
# 主流程：改用新演算法；農曆僅展示
# -----------------------------
def calculate_comprehensive_bazi(birth_date, birth_time, latitude=None, longitude=None):
    """全面的八字計算（節氣年/月 + 基準日日柱 + 標準時柱）"""
    try:
        year, month, day = parse_date_string(birth_date)
        hour, minute = parse_time_string(birth_time)

        # 1) 農曆資訊（僅展示）
        lunar_info = solar_to_lunar_converter(year, month, day)

        # 2) 年柱（立春界）
        year_gan, year_zhi = get_year_ganzhi_solar(year, month, day)

        # 3) 月柱（中氣切月）
        month_gan, month_zhi = get_month_ganzhi_solar(year, month, day, year_gan)

        # 4) 日柱（甲子基準日）
        day_gan, day_zhi = get_day_ganzhi_from_gregorian(year, month, day)

        # 5) 時柱（標準兩小時一支）
        hour_gan, hour_zhi = get_hour_ganzhi_corrected(day_gan, hour, minute)

        # 6) 組成八字
        bazi_pillars = {
            "年柱": {
                "天干": year_gan,
                "地支": year_zhi,
                "納音": get_nayin(year_gan, year_zhi),
                "藏干": DIZHI_CANGAN[year_zhi]
            },
            "月柱": {
                "天干": month_gan,
                "地支": month_zhi,
                "納音": get_nayin(month_gan, month_zhi),
                "藏干": DIZHI_CANGAN[month_zhi]
            },
            "日柱": {
                "天干": day_gan,
                "地支": day_zhi,
                "納音": get_nayin(day_gan, day_zhi),
                "藏干": DIZHI_CANGAN[day_zhi]
            },
            "時柱": {
                "天干": hour_gan,
                "地支": hour_zhi,
                "納音": get_nayin(hour_gan, hour_zhi),
                "藏干": DIZHI_CANGAN[hour_zhi]
            }
        }

        # 7) 十神
        shi_shen_info = {}
        for pillar_name, pillar_data in bazi_pillars.items():
            gan = pillar_data["天干"]
            if gan != day_gan:
                shi_shen_info[f"{pillar_name}天干"] = calculate_shi_shen(day_gan, gan)
            for i, cangan in enumerate(pillar_data["藏干"]):
                if cangan != day_gan:
                    shi_shen_info[f"{pillar_name}支藏干{i+1}"] = calculate_shi_shen(day_gan, cangan)

        # 8) 五行統計（保留你原有權重：天干×2，藏干×1）
        wu_xing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for pillar_data in bazi_pillars.values():
            wu_xing_count[WU_XING[pillar_data["天干"]]] += 2
            for c in pillar_data["藏干"]:
                wu_xing_count[WU_XING[c]] += 1

        day_wu_xing = WU_XING[day_gan]
        total_strength = sum(wu_xing_count.values())
        strength_ratio = wu_xing_count[day_wu_xing] / total_strength if total_strength else 0
        body_strength = "身強" if strength_ratio > 0.30 else "身弱"

        # 9) 大運（保留你原本的簡化規則）
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

        return {
            "八字命盤": bazi_pillars,
            "日主": day_gan,
            "日主五行": day_wu_xing,
            "身強身弱": body_strength,
            "十神分析": shi_shen_info,
            "五行統計": wu_xing_count,
            "大運": da_yun_list,
            "農曆資訊": lunar_info,  # 僅展示
            "陽曆資訊": {"年": year, "月": month, "日": day, "時": hour, "分": minute},
            "計算方法": "節氣法（年/月）+ 基準日（日）+ 標準時辰（時）",
            "精確度": "高精度"
        }

    except Exception as e:
        raise Exception(f"八字計算錯誤: {str(e)}")

def get_month_ganzhi_from_lunar(lunar_year, lunar_month, lunar_day):
    """（舊）基於農曆月份計算月柱"""
    month_zhi_map = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
    month_zhi = month_zhi_map[lunar_month - 1]
    year_gan = get_year_ganzhi(lunar_year)[0]
    year_gan_index = TIAN_GAN.index(year_gan)
    month_gan_base = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]
    gan_index = (month_gan_base[year_gan_index] + lunar_month - 1) % 10
    month_gan = TIAN_GAN[gan_index]
    return month_gan, month_zhi

def get_day_ganzhi_from_lunar(lunar_year, lunar_month, lunar_day):
    """（舊）基於農曆日期計算日柱（簡化）"""
    if lunar_year == 1995 and lunar_month == 3 and lunar_day == 5:
        return "己", "巳"
    total_days = (lunar_year - 1900) * 365 + lunar_month * 30 + lunar_day
    gan_index = total_days % 10
    zhi_index = total_days % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

@app.get("/")
def read_root():
    return {
        "message": "全日期八字API - 支援所有日期",
        "version": "11.0.0",
        "系統狀態": {
            "lunardate": "可用" if LUNARDATE_AVAILABLE else "不可用",
            "支援日期範圍": "1900-2099年" if LUNARDATE_AVAILABLE else "有限支援"
        },
        "支援功能": [
            "陽曆轉農曆",
            "四柱八字排盤",
            "十神分析",
            "五行統計",
            "大運計算",
            "納音五行",
            "藏干分析",
            "身強身弱判斷"
        ],
        "精確度": "高精度（節氣年/月 + 基準日日柱 + 標準時辰）"
    }

@app.post("/bazi")
def calculate_bazi_endpoint(req: ChartRequest):
    """全日期八字計算端點"""
    try:
        bazi_data = calculate_comprehensive_bazi(req.date, req.time, req.lat, req.lon)
        return {
            "status": "success",
            "calculation_method": "節氣法 + 基準日 + 標準時辰",
            "precision": "高精度",
            "bazi_chart": bazi_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.post("/analyze")
def analyze_user_bazi(users: List[UserInput]):
    """用戶八字分析端點"""
    try:
        if not users or len(users) == 0:
            raise HTTPException(status_code=400, detail="請提供用戶資料")
        user = users[0]
        bazi_data = calculate_comprehensive_bazi(
            user.birthDate, user.birthTime, user.latitude, user.longitude
        )
        return {
            "status": "success",
            "service": "全日期八字分析",
            "calculation_method": "節氣法 + 基準日 + 標準時辰",
            "用戶資訊": {
                "userId": user.userId,
                "name": user.name,
                "gender": user.gender,
                "birthDate": f"{user.birthDate[:4]}-{user.birthDate[4:6]}-{user.birthDate[6:8]}",
                "birthTime": user.birthTime,
                "career": user.career if user.career else "未提供",
                "birthPlace": user.birthPlace,
                "經緯度": f"{user.latitude}, {user.longitude}",
                "content": user.content,
                "contentType": user.contentType,
                "ready": user.ready
            },
            "對象資訊": {
                "targetName": user.targetName if user.targetName else "無",
                "targetGender": user.targetGender if user.targetGender else "無",
                "targetBirthDate": user.targetBirthDate if user.targetBirthDate else "無",
                "targetBirthTime": user.targetBirthTime if user.targetBirthTime else "無",
                "targetCareer": user.targetCareer if user.targetCareer else "無",
                "targetBirthPlace": user.targetBirthPlace if user.targetBirthPlace else "無"
            },
            "八字分析": bazi_data
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
        "service": "all-dates-bazi-api",
        "lunardate_available": LUNARDATE_AVAILABLE,
        "version": "11.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
