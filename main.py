from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import re
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

DIZHI_CANGAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"], "午": ["丁", "己"], "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"], "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"]
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
    clean_date = re.sub(r'[^0-9]', '', date_str)
    if len(clean_date) == 8:
        return int(clean_date[:4]), int(clean_date[4:6]), int(clean_date[6:8])
    return 2000, 1, 1

def parse_time_string(time_str):
    clean_time = time_str.strip().replace(' ', '')
    if ':' in clean_time:
        parts = clean_time.split(':')
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    return 12, 0

def get_year_ganzhi(year):
    gan_index = (year - 1984) % 10
    zhi_index = (year - 1984) % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_month_ganzhi(year, month, day):
    jieqi_days = {1: 6, 2: 4, 3: 6, 4: 5, 5: 6, 6: 6, 7: 7, 8: 8, 9: 8, 10: 8, 11: 7, 12: 7}
    
    if month == 1:
        lunar_month = 12 if day < jieqi_days[1] else 1
    elif month == 2:
        lunar_month = 1 if day < jieqi_days[2] else 2
    else:
        lunar_month = month - 1 if day >= jieqi_days[month] else month - 2
    
    lunar_month = ((lunar_month - 1) % 12) + 1
    month_zhi_map = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
    month_zhi = month_zhi_map[lunar_month - 1]
    
    year_gan = get_year_ganzhi(year)[0]
    year_gan_index = TIAN_GAN.index(year_gan)
    month_gan_base = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]
    gan_index = (month_gan_base[year_gan_index] + lunar_month - 1) % 10
    month_gan = TIAN_GAN[gan_index]
    
    return month_gan, month_zhi

def get_day_ganzhi(year, month, day):
    base_date = date(2000, 1, 1)
    target_date = date(year, month, day)
    days_diff = (target_date - base_date).days
    
    base_gan = 4
    base_zhi = 6
    
    gan_index = (base_gan + days_diff) % 10
    zhi_index = (base_zhi + days_diff) % 12
    
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_hour_ganzhi(day_gan, hour, minute):
    # 正确的时辰划分
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
        zhi_index = 6
    
    hour_zhi = DI_ZHI[zhi_index]
    
    day_gan_index = TIAN_GAN.index(day_gan)
    hour_gan_base = [0, 2, 4, 6, 8, 0, 2, 4, 6, 8]
    gan_index = (hour_gan_base[day_gan_index] + zhi_index) % 10
    hour_gan = TIAN_GAN[gan_index]
    
    return hour_gan, hour_zhi

def get_nayin(gan, zhi):
    return NAYIN.get(gan + zhi, "未知")

def calculate_bazi(birth_date, birth_time):
    year, month, day = parse_date_string(birth_date)
    hour, minute = parse_time_string(birth_time)
    
    year_gan, year_zhi = get_year_ganzhi(year)
    month_gan, month_zhi = get_month_ganzhi(year, month, day)
    day_gan, day_zhi = get_day_ganzhi(year, month, day)
    hour_gan, hour_zhi = get_hour_ganzhi(day_gan, hour, minute)
    
    return {
        "八字命盤": {
            "年柱": {"天干": year_gan, "地支": year_zhi, "納音": get_nayin(year_gan, year_zhi)},
            "月柱": {"天干": month_gan, "地支": month_zhi, "納音": get_nayin(month_gan, month_zhi)},
            "日柱": {"天干": day_gan, "地支": day_zhi, "納音": get_nayin(day_gan, day_zhi)},
            "時柱": {"天干": hour_gan, "地支": hour_zhi, "納音": get_nayin(hour_gan, hour_zhi)}
        },
        "日主": day_gan,
        "完整八字": f"{year_gan}{year_zhi} {month_gan}{month_zhi} {day_gan}{day_zhi} {hour_gan}{hour_zhi}"
    }

@app.get("/")
def read_root():
    return {"message": "八字API", "version": "1.0.0", "status": "运行中"}

@app.post("/bazi")
def calculate_bazi_endpoint(req: ChartRequest):
    try:
        result = calculate_bazi(req.date, req.time)
        return {"status": "success", "bazi_chart": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/analyze")
def analyze_user_bazi(users: List[UserInput]):
    try:
        if not users:
            raise HTTPException(status_code=400, detail="请提供用户资料")
        
        user = users[0]
        result = calculate_bazi(user.birthDate, user.birthTime)
        
        return {
            "status": "success",
            "用戶資訊": {"name": user.name, "birthDate": user.birthDate, "birthTime": user.birthTime},
            "八字分析": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
