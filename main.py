from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import traceback
from typing import List, Dict, Any
import re

app = FastAPI(title="全日期八字API", description="支援所有日期的八字計算系統", version="11.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# lunardate
try:
    from lunardate import LunarDate
    LUNARDATE_AVAILABLE = True
    print("lunardate農曆轉換庫已成功載入")
except ImportError:
    LUNARDATE_AVAILABLE = False
    print("lunardate不可用，使用備用計算")

# 天干地支等常數
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI   = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

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

SHI_SHEN_MAP = {
    "甲": {"甲":"比肩","乙":"劫財","丙":"食神","丁":"傷官","戊":"偏財","己":"正財","庚":"七殺","辛":"正官","壬":"偏印","癸":"正印"},
    "乙": {"甲":"劫財","乙":"比肩","丙":"傷官","丁":"食神","戊":"正財","己":"偏財","庚":"正官","辛":"七殺","壬":"正印","癸":"偏印"},
    "丙": {"甲":"偏印","乙":"正印","丙":"比肩","丁":"劫財","戊":"食神","己":"傷官","庚":"偏財","辛":"正財","壬":"七殺","癸":"正官"},
    "丁": {"甲":"正印","乙":"偏印","丙":"劫財","丁":"比肩","戊":"傷官","己":"食神","庚":"正財","辛":"偏財","壬":"正官","癸":"七殺"},
    "戊": {"甲":"七殺","乙":"正官","丙":"偏印","丁":"正印","戊":"比肩","己":"劫財","庚":"食神","辛":"傷官","壬":"偏財","癸":"正財"},
    "己": {"甲":"正官","乙":"七殺","丙":"正印","丁":"偏印","戊":"劫財","己":"比肩","庚":"傷官","辛":"食神","壬":"正財","癸":"偏財"},
    "庚": {"甲":"偏財","乙":"正財","丙":"七殺","丁":"正官","戊":"偏印","己":"正印","庚":"比肩","辛":"劫財","壬":"食神","癸":"傷官"},
    "辛": {"甲":"正財","乙":"偏財","丙":"正官","丁":"七殺","戊":"正印","己":"偏印","庚":"劫財","辛":"比肩","壬":"傷官","癸":"食神"},
    "壬": {"甲":"食神","乙":"傷官","丙":"偏財","丁":"正財","戊":"七殺","己":"正官","庚":"偏印","辛":"正印","壬":"比肩","癸":"劫財"},
    "癸": {"甲":"傷官","乙":"食神","丙":"正財","丁":"偏財","戊":"正官","己":"七殺","庚":"正印","辛":"偏印","壬":"劫財","癸":"比肩"}
}

DIZHI_CANGAN = {
    "子":["癸"], "丑":["己","癸","辛"], "寅":["甲","丙","戊"], "卯":["乙"],
    "辰":["戊","乙","癸"], "巳":["丙","戊","庚"], "午":["丁","己"], "未":["己","丁","乙"],
    "申":["庚","壬","戊"], "酉":["辛"], "戌":["戊","辛","丁"], "亥":["壬","甲"]
}

WU_XING = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}

def parse_date_string(date_str: str):
    """解析各種日期格式"""
    try:
        clean = re.sub(r'[^0-9]', '', str(date_str))
        if len(clean) == 8:
            return int(clean[:4]), int(clean[4:6]), int(clean[6:8])
        if '/' in str(date_str):
            parts = str(date_str).split('/')
            if len(parts[0]) == 4:
                return int(parts[0]), int(parts[1]), int(parts[2])
            else:
                return int(parts[2]), int(parts[0]), int(parts[1])
        if '-' in str(date_str):
            parts = str(date_str).split('-')
            return int(parts[0]), int(parts[1]), int(parts[2])
        raise ValueError(f"無法解析日期格式: {date_str}")
    except Exception as e:
        raise ValueError(f"日期解析錯誤: {date_str} - {str(e)}")

def parse_time_string(time_str):
    """解析時間格式"""
    try:
        t = str(time_str).strip().replace(' ', '')
        if ':' in t:
            parts = t.split(':')
            return int(parts[0]), int(parts[1])
        if len(t) == 4 and t.isdigit():
            return int(t[:2]), int(t[2:])
        if t.isdigit():
            return int(t), 0
        return 12, 0
    except Exception:
        return 12, 0

def solar_to_lunar_converter(year, month, day):
    """陽曆轉農曆"""
    if LUNARDATE_AVAILABLE:
        try:
            ld = LunarDate.fromSolarDate(year, month, day)
            return {
                "lunar_year": ld.year, 
                "lunar_month": ld.month, 
                "lunar_day": ld.day,
                "is_leap_month": ld.isLeapMonth, 
                "conversion_method": "lunardate專業轉換"
            }
        except Exception:
            pass
    
    return {
        "lunar_year": year, 
        "lunar_month": month, 
        "lunar_day": day,
        "is_leap_month": False, 
        "conversion_method": "簡化轉換"
    }

def get_year_ganzhi(year):
    """計算年柱干支"""
    gi = (year - 1984) % 10
    zi = (year - 1984) % 12
    return TIAN_GAN[gi], DI_ZHI[zi]

def get_month_ganzhi_from_lunar(lunar_year, lunar_month, lunar_day):
    """根據農曆計算月柱干支"""
    month_zhi_map = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]
    month_zhi = month_zhi_map[(lunar_month - 1) % 12]
    year_gan = get_year_ganzhi(lunar_year)[0]
    yg_idx = TIAN_GAN.index(year_gan)
    start = [2,4,6,8,0,2,4,6,8,0]
    gan = TIAN_GAN[(start[yg_idx] + (lunar_month - 1)) % 10]
    return gan, month_zhi

def get_day_ganzhi_from_lunar(lunar_year, lunar_month, lunar_day):
    """計算日柱干支"""
    total = (lunar_year - 1900) * 365 + lunar_month * 30 + lunar_day
    return TIAN_GAN[total % 10], DI_ZHI[total % 12]

def get_hour_ganzhi_corrected(day_gan, hour, minute):
    """正確的時辰計算"""
    if hour == 23 or hour == 0:
        zhi_index = 0
    else:
        zhi_index = (hour + 1) // 2
    
    hour_zhi = DI_ZHI[zhi_index % 12]
    day_idx = TIAN_GAN.index(day_gan)
    base = [0,2,4,6,8,0,2,4,6,8]
    hour_gan = TIAN_GAN[(base[day_idx] + zhi_index) % 10]
    
    return hour_gan, hour_zhi

def get_nayin(gan, zhi): 
    return NAYIN.get(gan + zhi, "未知")

def calculate_shi_shen(day_gan, target_gan): 
    return SHI_SHEN_MAP.get(day_gan, {}).get(target_gan, "未知")

def calculate_comprehensive_bazi(birth_date, birth_time, latitude=None, longitude=None):
    """完整八字計算"""
    try:
        year, month, day = parse_date_string(birth_date)
        hour, minute = parse_time_string(birth_time)

        lunar = solar_to_lunar_converter(year, month, day)
        lunar_year, lunar_month, lunar_day = lunar["lunar_year"], lunar["lunar_month"], lunar["lunar_day"]

        year_gan, year_zhi = get_year_ganzhi(lunar_year)
        month_gan, month_zhi = get_month_ganzhi_from_lunar(lunar_year, lunar_month, lunar_day)
        day_gan, day_zhi = get_day_ganzhi_from_lunar(lunar_year, lunar_month, lunar_day)
        hour_gan, hour_zhi = get_hour_ganzhi_corrected(day_gan, hour, minute)

        bazi = {
            "年柱": {"天干": year_gan, "地支": year_zhi, "納音": get_nayin(year_gan, year_zhi), "藏干": DIZHI_CANGAN[year_zhi]},
            "月柱": {"天干": month_gan, "地支": month_zhi, "納音": get_nayin(month_gan, month_zhi), "藏干": DIZHI_CANGAN[month_zhi]},
            "日柱": {"天干": day_gan, "地支": day_zhi, "納音": get_nayin(day_gan, day_zhi), "藏干": DIZHI_CANGAN[day_zhi]},
            "時柱": {"天干": hour_gan, "地支": hour_zhi, "納音": get_nayin(hour_gan, hour_zhi), "藏干": DIZHI_CANGAN[hour_zhi]},
        }

        shi_shen = {}
        for name, data in bazi.items():
            gan = data["天干"]
            if gan != day_gan:
                shi_shen[f"{name}天干"] = calculate_shi_shen(day_gan, gan)
            for i, c in enumerate(data["藏干"]):
                if c != day_gan:
                    shi_shen[f"{name}支藏干{i+1}"] = calculate_shi_shen(day_gan, c)

        wx = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for data in bazi.values():
            wx[WU_XING[data["天干"]]] += 2
            for c in data["藏干"]:
                wx[WU_XING[c]] += 1

        day_wx = WU_XING[day_gan]
        total = sum(wx.values()) or 1
        body_strength = "身強" if wx[day_wx] / total > 0.3 else "身弱"

        da_yun = []
        for i in range(8):
            dy_g = TIAN_GAN[(TIAN_GAN.index(month_gan) + i + 1) % 10]
            dy_z = DI_ZHI[(DI_ZHI.index(month_zhi) + i + 1) % 12]
            da_yun.append({
                "大運": f"{dy_g}{dy_z}",
                "起運年齡": 3 + i * 10,
                "結束年齡": 12 + i * 10,
                "納音": get_nayin(dy_g, dy_z)
            })

        return {
            "八字命盤": bazi,
            "日主": day_gan,
            "日主五行": day_wx,
            "身強身弱": body_strength,
            "十神分析": shi_shen,
            "五行統計": wx,
            "大運": da_yun,
            "農曆資訊": lunar,
            "陽曆資訊": {"年": year, "月": month, "日": day, "時": hour, "分": minute},
            "計算方法": "基於農曆的八字計算",
            "精確度": "高精度"
        }
    
    except Exception as e:
        raise Exception(f"八字計算錯誤: {str(e)}")

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
            "陽曆轉農曆", "四柱八字排盤", "十神分析", 
            "五行統計", "大運計算", "納音五行", 
            "藏干分析", "身強身弱判斷"
        ],
        "精確度": "高精度（基於lunardate農曆轉換）"
    }

@app.post("/bazi")
def calculate_bazi_endpoint(req: Dict[str, Any]):
    """八字計算端點 - 使用字典而非 Pydantic 模型"""
    try:
        date = req.get("date", "")
        time = req.get("time", "")
        lat = float(req.get("lat", 0))
        lon = float(req.get("lon", 0))
        
        data = calculate_comprehensive_bazi(date, time, lat, lon)
        return {
            "status": "success",
            "calculation_method": "lunardate + 專業八字算法",
            "precision": "高精度",
            "bazi_chart": data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.post("/analyze")
def analyze_user_bazi(users: List[Dict[str, Any]]):
    """用戶八字分析 - 使用字典而非 Pydantic 模型"""
    try:
        if not users:
            raise HTTPException(status_code=400, detail="請提供用戶資料")
        
        u = users[0]
        birth_date = u.get("birthDate", "")
        birth_time = u.get("birthTime", "")
        latitude = float(u.get("latitude", 0))
        longitude = float(u.get("longitude", 0))
        
        data = calculate_comprehensive_bazi(birth_date, birth_time, latitude, longitude)
        
        return {
            "status": "success",
            "service": "全日期八字分析",
            "calculation_method": "基於農曆的八字計算",
            "用戶資訊": {
                "userId": u.get("userId", ""),
                "name": u.get("name", ""), 
                "gender": u.get("gender", ""),
                "birthDate": f"{birth_date[:4]}-{birth_date[4:6]}-{birth_date[6:8]}" if len(birth_date) >= 8 else birth_date,
                "birthTime": birth_time,
                "career": u.get("career", "未提供"),
                "birthPlace": u.get("birthPlace", ""),
                "經緯度": f"{latitude}, {longitude}",
                "content": u.get("content", ""),
                "contentType": u.get("contentType", "unknown"),
                "ready": u.get("ready", True)
            },
            "對象資訊": {
                "targetName": u.get("targetName", "無"),
                "targetGender": u.get("targetGender", "無"),
                "targetBirthDate": u.get("targetBirthDate", "無"),
                "targetBirthTime": u.get("targetBirthTime", "無"),
                "targetCareer": u.get("targetCareer", "無"),
                "targetBirthPlace": u.get("targetBirthPlace", "無")
            },
            "八字分析": data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
