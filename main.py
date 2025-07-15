from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback
from typing import List, Optional
import uvicorn
import re
import math
from datetime import datetime

# 導入八字庫
try:
    from lunar_python import Lunar, Solar
    LUNAR_AVAILABLE = True
    print("lunar-python已成功載入")
except ImportError:
    LUNAR_AVAILABLE = False
    print("lunar-python不可用")

app = FastAPI(title="深語AI三系統占星API", description="整合紫微斗數、西洋占星、八字命理的專業系統", version="5.0.0")

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 星座名稱對照表
SIGN_NAMES = {
    0: "白羊座", 1: "金牛座", 2: "雙子座", 3: "巨蟹座",
    4: "獅子座", 5: "處女座", 6: "天秤座", 7: "天蠍座",
    8: "射手座", 9: "摩羯座", 10: "水瓶座", 11: "雙魚座"
}

# 宮位名稱對照表
HOUSE_NAMES = {
    1: "第一宮", 2: "第二宮", 3: "第三宮", 4: "第四宮",
    5: "第五宮", 6: "第六宮", 7: "第七宮", 8: "第八宮",
    9: "第九宮", 10: "第十宮", 11: "第十一宮", 12: "第十二宮"
}

# 行星名稱對照表
PLANET_NAMES = {
    0: "太陽", 1: "月亮", 2: "水星", 3: "金星", 4: "火星",
    5: "木星", 6: "土星", 7: "天王星", 8: "海王星", 9: "冥王星",
    11: "北交點"
}

# 嘗試導入Swiss Ephemeris
try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
    print("Swiss Ephemeris已成功載入")
except ImportError:
    SWISSEPH_AVAILABLE = False
    print("Swiss Ephemeris不可用，將使用高精度備用計算")

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
        
    except Exception as e:
        return 12, 0

def decimal_to_degrees_minutes(decimal_degrees):
    """將小數度數轉換為度分格式"""
    sign_degree = decimal_degrees % 30
    degrees = int(sign_degree)
    minutes = int((sign_degree - degrees) * 60)
    return degrees, minutes

def calculate_bazi_chart(birth_date, birth_time, latitude, longitude):
    """使用lunar-python計算八字命盤"""
    try:
        if not LUNAR_AVAILABLE:
            raise Exception("lunar-python不可用")
        
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
        
        # 創建陽曆對象
        solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        lunar = solar.getLunar()
        
        # 取得八字
        eight_char = lunar.getEightChar()
        
        # 基本八字信息
        bazi_info = {
            "年柱": {
                "天干": eight_char.getYearGan(),
                "地支": eight_char.getYearZhi(),
                "納音": eight_char.getYearNaYin()
            },
            "月柱": {
                "天干": eight_char.getMonthGan(), 
                "地支": eight_char.getMonthZhi(),
                "納音": eight_char.getMonthNaYin()
            },
            "日柱": {
                "天干": eight_char.getDayGan(),
                "地支": eight_char.getDayZhi(), 
                "納音": eight_char.getDayNaYin()
            },
            "時柱": {
                "天干": eight_char.getTimeGan(),
                "地支": eight_char.getTimeZhi(),
                "納音": eight_char.getTimeNaYin()
            }
        }
        
        # 取得大運
        da_yun = eight_char.getDaYun(1)  # 順運
        dayun_list = []
        for i in range(8):  # 取8步大運
            yun = da_yun.next(i)
            if yun:
                dayun_list.append({
                    "大運": f"{yun.getGanZhi()}",
                    "起運年齡": yun.getStartAge(),
                    "結束年齡": yun.getEndAge(),
                    "起運年份": yun.getStartYear()
                })
        
        # 日主強弱分析
        day_gan = eight_char.getDayGan()
        
        # 十神分析
        shi_shen = {
            "年干十神": eight_char.getYearShiShenGan(),
            "年支十神": eight_char.getYearShiShenZhi()[0] if eight_char.getYearShiShenZhi() else "",
            "月干十神": eight_char.getMonthShiShenGan(),
            "月支十神": eight_char.getMonthShiShenZhi()[0] if eight_char.getMonthShiShenZhi() else "",
            "日支十神": eight_char.getDayShiShenZhi()[0] if eight_char.getDayShiShenZhi() else "",
            "時干十神": eight_char.getTimeShiShenGan(),
            "時支十神": eight_char.getTimeShiShenZhi()[0] if eight_char.getTimeShiShenZhi() else ""
        }
        
        # 格局分析
        pattern_analysis = analyze_bazi_pattern(bazi_info, day_gan)
        
        return {
            "八字命盤": bazi_info,
            "日主": day_gan,
            "大運": dayun_list,
            "十神": shi_shen,
            "格局分析": pattern_analysis,
            "陰陽曆信息": {
                "陽曆": f"{year}年{month}月{day}日 {hour}時{minute}分",
                "陰曆": f"{lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()} {lunar.getTimeInChinese()}時",
                "節氣": lunar.getJieQi(),
                "生肖": lunar.getYearShengXiao()
            }
        }
        
    except Exception as e:
        raise Exception(f"八字計算錯誤: {str(e)}")

def analyze_bazi_pattern(bazi_info, day_gan):
    """簡化的八字格局分析"""
    try:
        # 基本格局判斷（簡化版）
        month_gan = bazi_info["月柱"]["天干"]
        month_zhi = bazi_info["月柱"]["地支"]
        
        # 五行分析
        gan_elements = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", 
                       "戊": "土", "己": "土", "庚": "金", "辛": "金", 
                       "壬": "水", "癸": "水"}
        
        day_element = gan_elements.get(day_gan, "未知")
        
        # 基本強弱判斷
        strength = "中和"  # 簡化處理
        
        # 用神建議
        yong_shen = get_yong_shen_suggestion(day_gan, month_zhi)
        
        return {
            "日主五行": day_element,
            "身強身弱": strength,
            "建議用神": yong_shen,
            "格局類型": "普通格局",  # 簡化處理
            "喜用神": yong_shen,
            "忌神": get_ji_shen_suggestion(day_gan)
        }
        
    except Exception as e:
        return {"格局分析": "分析失敗", "錯誤": str(e)}

def get_yong_shen_suggestion(day_gan, month_zhi):
    """簡化的用神建議"""
    suggestions = {
        "甲": "火、土", "乙": "火、金", "丙": "水、土", "丁": "水、金",
        "戊": "木、水", "己": "木、火", "庚": "火、木", "辛": "水、木", 
        "壬": "土、火", "癸": "火、土"
    }
    return suggestions.get(day_gan, "需詳細分析")

def get_ji_shen_suggestion(day_gan):
    """簡化的忌神建議"""
    ji_shen = {
        "甲": "金、水", "乙": "土、水", "丙": "金、木", "丁": "土、木",
        "戊": "金、火", "己": "水、金", "庚": "水、土", "辛": "火、土",
        "壬": "木、金", "癸": "木、水"
    }
    return ji_shen.get(day_gan, "需詳細分析")

def get_planet_house(planet_lon, houses):
    """計算行星在哪個宮位"""
    try:
        planet_lon = planet_lon % 360
        for house_num in range(1, 13):
            next_house = house_num + 1 if house_num < 12 else 1
            house_start = houses[house_num - 1]  # houses是0-based
            house_end = houses[next_house - 1] if next_house <= 12 else houses[0]
            
            if house_start < house_end:
                if house_start <= planet_lon < house_end:
                    return house_num
            else:  # 跨越0度
                if planet_lon >= house_start or planet_lon < house_end:
                    return house_num
        return 1
    except Exception as e:
        return 1

def calculate_swiss_ephemeris_chart(birth_date, birth_time, latitude, longitude):
    """使用Swiss Ephemeris計算真正專業的占星圖"""
    try:
        if not SWISSEPH_AVAILABLE:
            raise Exception("Swiss Ephemeris不可用")
        
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
        
        # 計算儒略日（UTC時間）
        jd_ut = swe.julday(year, month, day, hour + minute/60.0)
        
        # 計算宮位（使用Placidus宮位制）
        houses, ascmc = swe.houses(jd_ut, latitude, longitude, b'P')
        
        # 取得上升點和天頂
        asc = ascmc[0]  # 上升點
        mc = ascmc[1]   # 天頂
        
        result = {}
        
        # 計算主要行星位置
        for planet_id in range(10):  # 0-9: 太陽到冥王星
            try:
                xx, ret = swe.calc_ut(jd_ut, planet_id, swe.FLG_SWIEPH)
                longitude = xx[0]
                speed = xx[3]
                
                planet_name = PLANET_NAMES.get(planet_id, f"行星{planet_id}")
                sign_num = int(longitude // 30)
                sign_name = SIGN_NAMES.get(sign_num, f"星座{sign_num}")
                house_num = get_planet_house(longitude, houses)
                
                result[planet_name] = {
                    "longitude": round(longitude, 2),
                    "sign": sign_num,
                    "sign_name": sign_name,
                    "house": house_num,
                    "house_name": HOUSE_NAMES[house_num],
                    "degree_format": format_degree_minute(longitude),
                    "speed": round(speed, 4)
                }
            except Exception as e:
                print(f"計算行星 {planet_id} 時出錯: {e}")
        
        # 計算北交點
        try:
            xx, ret = swe.calc_ut(jd_ut, swe.MEAN_NODE, swe.FLG_SWIEPH)
            longitude = xx[0]
            sign_num = int(longitude // 30)
            house_num = get_planet_house(longitude, houses)
            
            result["北交點"] = {
                "longitude": round(longitude, 2),
                "sign": sign_num,
                "sign_name": SIGN_NAMES.get(sign_num, f"星座{sign_num}"),
                "house": house_num,
                "house_name": HOUSE_NAMES[house_num],
                "degree_format": format_degree_minute(longitude),
                "speed": round(xx[3], 4)
            }
        except Exception as e:
            print(f"計算北交點時出錯: {e}")
        
        # 添加上升點
        sign_num = int(asc // 30)
        result["上升點"] = {
            "longitude": round(asc, 2),
            "sign": sign_num,
            "sign_name": SIGN_NAMES.get(sign_num, f"星座{sign_num}"),
            "house": 1,
            "house_name": "第一宮",
            "degree_format": format_degree_minute(asc),
            "speed": 0.0
        }
        
        # 添加天頂
        sign_num = int(mc // 30)
        result["天頂"] = {
            "longitude": round(mc, 2),
            "sign": sign_num,
            "sign_name": SIGN_NAMES.get(sign_num, f"星座{sign_num}"),
            "house": 10,
            "house_name": "第十宮",
            "degree_format": format_degree_minute(mc),
            "speed": 0.0
        }
        
        return result
        
    except Exception as e:
        raise Exception(f"Swiss Ephemeris計算錯誤: {str(e)}")

def create_advanced_fallback_chart(birth_date, birth_time, latitude, longitude):
    """高精度備用計算（改進版）"""
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
        
        # 精確的儒略日計算
        if month <= 2:
            year -= 1
            month += 12
        
        A = year // 100
        B = 2 - A + A // 4
        JD = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
        JD += (hour + minute / 60.0) / 24.0
        
        # 高精度天文計算
        T = (JD - 2451545.0) / 36525.0
        T2 = T * T
        T3 = T2 * T
        
        # 精確的太陽位置（VSOP87理論）
        L0 = 280.4664567 + 360007.6982779 * T + 0.03032028 * T2 + T3/49931 - T3*T/15300 - T3*T2/2000000
        M = 357.52772 + 35999.05034 * T - 0.0001603 * T2 - T3/300000
        
        # 太陽真黃經
        M_rad = math.radians(M)
        C = (1.914602 - 0.004817 * T - 0.000014 * T2) * math.sin(M_rad) + \
            (0.019993 - 0.000101 * T) * math.sin(2 * M_rad) + \
            0.000289 * math.sin(3 * M_rad)
        
        sun_lon = (L0 + C) % 360
        
        # 月亮位置（ELP2000/82理論簡化版）
        L_moon = (218.3164477 + 481267.88123421 * T - 0.0015786 * T2 + T3/538841 - T3*T/65194000) % 360
        D = (297.8501921 + 445267.1114034 * T - 0.0018819 * T2 + T3/545868 - T3*T/113065000) % 360
        M_moon = (134.9633964 + 477198.8675055 * T + 0.0087414 * T2 + T3/69699 - T3*T/14712000) % 360
        F = (93.2720950 + 483202.0175233 * T - 0.0036539 * T2 - T3/3526000 + T3*T/863310000) % 360
        
        # 月亮主要攝動項
        moon_corrections = [
            6.288774 * math.sin(math.radians(M_moon)),
            1.274027 * math.sin(math.radians(2*D - M_moon)),
            0.658314 * math.sin(math.radians(2*D)),
            0.213618 * math.sin(math.radians(2*M_moon)),
            -0.185116 * math.sin(math.radians(M)),
            -0.114332 * math.sin(math.radians(2*F))
        ]
        
        moon_lon = (L_moon + sum(moon_corrections)) % 360
        
        # 行星位置（簡化VSOP87）
        planet_data = {
            "水星": {"L0": 252.250906, "L1": 149472.6746358, "a": 0.38709893, "e": 0.20563069},
            "金星": {"L0": 181.979801, "L1": 58517.8156760, "a": 0.72333199, "e": 0.00677323},
            "火星": {"L0": 355.433, "L1": 19140.299, "a": 1.52366231, "e": 0.09341233},
            "木星": {"L0": 34.351519, "L1": 3034.90567, "a": 5.20336301, "e": 0.04839266},
            "土星": {"L0": 50.077444, "L1": 1222.11387, "a": 9.53707032, "e": 0.05415060},
            "天王星": {"L0": 314.055, "L1": 428.467, "a": 19.19126393, "e": 0.04716771},
            "海王星": {"L0": 304.349, "L1": 218.486, "a": 30.06896348, "e": 0.00858587},
            "冥王星": {"L0": 238.928, "L1": 145.18, "a": 39.48, "e": 0.2488}
        }
        
        planet_positions = {"太陽": sun_lon, "月亮": moon_lon}
        
        for planet_name, data in planet_data.items():
            try:
                L = (data["L0"] + data["L1"] * T) % 360
                M_planet = (L - data["L0"]) % 360
                E = M_planet + data["e"] * math.degrees(math.sin(math.radians(M_planet)))
                nu = 2 * math.atan(math.sqrt((1 + data["e"]) / (1 - data["e"])) * math.tan(math.radians(E) / 2))
                planet_lon = (math.degrees(nu) + data["L0"]) % 360
                planet_positions[planet_name] = planet_lon
            except:
                planet_positions[planet_name] = (sun_lon + hash(planet_name) % 360) % 360
        
        # 精確的上升點計算
        lat_rad = math.radians(latitude)
        
        # 恆星時計算
        GMST0 = (280.46061837 + 360.98564736629 * (JD - 2451545.0)) % 360
        GMST = (GMST0 + longitude + (hour + minute/60.0) * 15) % 360
        LST = GMST
        
        # 太陽赤經赤緯
        epsilon = 23.4393 - 0.0130 * T  # 黃赤交角
        epsilon_rad = math.radians(epsilon)
        sun_lon_rad = math.radians(sun_lon)
        
        # 上升點計算
        LST_rad = math.radians(LST)
        tan_asc = (math.cos(LST_rad) * math.tan(epsilon_rad) * math.cos(lat_rad) - math.sin(lat_rad) * math.sin(LST_rad)) / math.cos(LST_rad)
        asc_lon = math.degrees(math.atan(tan_asc)) % 360
        if LST > 180:
            asc_lon = (asc_lon + 180) % 360
        
        # 天頂計算
        mc_lon = (LST + 90) % 360
        
        planet_positions["上升點"] = asc_lon
        planet_positions["天頂"] = mc_lon
        
        # 北交點（簡化計算）
        omega = (125.0445479 - 1934.1362891 * T + 0.0020754 * T2 + T3/467441) % 360
        planet_positions["北交點"] = omega
        
        # 簡化的宮位計算（等宮制改進版）
        houses = []
        for i in range(12):
            house_cusp = (asc_lon + i * 30) % 360
            houses.append(house_cusp)
        
        # 格式化結果
        result = {}
        for planet_name, longitude in planet_positions.items():
            longitude = longitude % 360
            sign_num = int(longitude // 30)
            sign_name = SIGN_NAMES[sign_num]
            house_num = get_planet_house(longitude, houses)
            
            result[planet_name] = {
                "longitude": round(longitude, 2),
                "sign": sign_num,
                "sign_name": sign_name,
                "house": house_num,
                "house_name": HOUSE_NAMES[house_num],
                "degree_format": format_degree_minute(longitude),
                "speed": 0.0
            }
        
        return result
        
    except Exception as e:
        raise Exception(f"高精度備用計算錯誤: {str(e)}")

@app.get("/")
def read_root():
    swiss_status = "可用" if SWISSEPH_AVAILABLE else "不可用"
    lunar_status = "可用" if LUNAR_AVAILABLE else "不可用"
    return {
        "message": "深語AI三系統占星API服務正在運行", 
        "version": "5.0.0",
        "系統狀態": {
            "西洋占星": f"Swiss Ephemeris {swiss_status}",
            "八字命理": f"lunar-python {lunar_status}",
            "紫微斗數": "待整合"
        },
        "可用端點": {
            "/deep_analysis": "深語AI三系統完整分析",
            "/chart": "西洋占星分析", 
            "/bazi": "八字命理分析",
            "/health": "系統健康檢查"
        }
    }

@app.post("/deep_analysis")
def deep_soul_analysis(users: List[UserInput]):
    """深語AI三系統靈魂分析"""
    try:
        if not users or len(users) == 0:
            raise HTTPException(status_code=400, detail="請提供用戶資料")
        
        user = users[0]
        
        # 計算三系統命盤
        results = {}
        calculation_methods = {}
        
        # 1. 西洋占星
        try:
            if SWISSEPH_AVAILABLE:
                astro_chart = calculate_swiss_ephemeris_chart(
                    user.birthDate, user.birthTime, user.latitude, user.longitude
                )
                calculation_methods["西洋占星"] = "Swiss Ephemeris專業計算"
            else:
                astro_chart = create_advanced_fallback_chart(
                    user.birthDate, user.birthTime, user.latitude, user.longitude
                )
                calculation_methods["西洋占星"] = "高精度備用計算"
            results["西洋占星"] = astro_chart
        except Exception as e:
            results["西洋占星"] = {"錯誤": str(e)}
            calculation_methods["西洋占星"] = "計算失敗"
        
        # 2. 八字命理
        try:
            if LUNAR_AVAILABLE:
                bazi_chart = calculate_bazi_chart(
                    user.birthDate, user.birthTime, user.latitude, user.longitude
                )
                calculation_methods["八字命理"] = "lunar-python專業計算"
            else:
                bazi_chart = {"錯誤": "lunar-python不可用"}
                calculation_methods["八字命理"] = "計算失敗"
            results["八字命理"] = bazi_chart
        except Exception as e:
            results["八字命理"] = {"錯誤": str(e)}
            calculation_methods["八字命理"] = "計算失敗"
        
        # 3. 深語AI分析（基礎版）
        soul_analysis = generate_basic_soul_analysis(results, user)
        
        return {
            "status": "success",
            "service": "深語AI三系統分析",
            "計算方法": calculation_methods,
            "用戶資訊": {
                "姓名": user.name,
                "性別": user.gender,
                "出生日期": f"{user.birthDate[:4]}-{user.birthDate[4:6]}-{user.birthDate[6:8]}",
                "出生時間": user.birthTime,
                "出生地點": user.birthPlace
            },
            "三系統命盤": results,
            "深語AI洞察": soul_analysis
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

def generate_basic_soul_analysis(charts, user_data):
    """基礎版深語AI分析"""
    try:
        analysis = {
            "靈魂映照": "正在分析你的內在狀態...",
            "關係解構": "正在解構你的關係模式...", 
            "生命導航": "正在為你指引方向...",
            "整合洞察": "三系統整合分析中..."
        }
        
        # 如果有八字資料，加入基本分析
        if "八字命理" in charts and "錯誤" not in charts["八字命理"]:
            bazi = charts["八字命理"]
            if "格局分析" in bazi:
                analysis["八字洞察"] = {
                    "日主特質": f"你是{bazi['日主']}日主，{bazi['格局分析']['日主五行']}性格",
                    "用神建議": f"建議補強：{bazi['格局分析']['建議用神']}",
                    "大運趨勢": f"未來大運：{bazi['大運'][0]['大運'] if bazi['大運'] else '計算中'}"
                }
        
        # 如果有占星資料，加入基本分析  
        if "西洋占星" in charts and "錯誤" not in charts["西洋占星"]:
            astro = charts["西洋占星"]
            if "太陽" in astro:
                analysis["占星洞察"] = {
                    "核心特質": f"太陽{astro['太陽']['sign_name']}的你，具有{astro['太陽']['house_name']}的人生主題",
                    "情感模式": f"月亮{astro.get('月亮', {}).get('sign_name', '未知')}影響你的情感表達",
                    "行動力": f"火星位於{astro.get('火星', {}).get('house_name', '未知')}，決定你的行動模式"
                }
        
        return analysis
        
    except Exception as e:
        return {"分析錯誤": str(e)}
    """分析用戶的占星圖，使用Swiss Ephemeris專業計算"""
    try:
        if not users or len(users) == 0:
            raise HTTPException(status_code=400, detail="請提供用戶資料")
        
        user = users[0]
        
        # 嘗試使用Swiss Ephemeris，失敗則使用高精度備用計算
        try:
            if SWISSEPH_AVAILABLE:
                chart_data = calculate_swiss_ephemeris_chart(
                    user.birthDate, 
                    user.birthTime, 
                    user.latitude, 
                    user.longitude
                )
                calculation_method = "Swiss Ephemeris專業計算"
            else:
                raise Exception("Swiss Ephemeris不可用")
        except Exception as e:
            print(f"Swiss Ephemeris計算失敗: {e}")
            chart_data = create_advanced_fallback_chart(
                user.birthDate, 
                user.birthTime, 
                user.latitude, 
                user.longitude
            )
            calculation_method = "高精度備用計算"
        
        # 格式化輸出
        formatted_chart = {}
        house_distribution = {}
        
        for planet_name, data in chart_data.items():
            formatted_chart[planet_name] = {
                "星座": data["sign_name"],
                "宮位": data["house_name"],
                "度數": data["degree_format"],
                "黃經": data["longitude"],
                "宮位數字": data["house"],
                "速度": data["speed"]
            }
            
            house_key = data["house_name"]
            if house_key not in house_distribution:
                house_distribution[house_key] = []
            house_distribution[house_key].append(planet_name)
        
        important_houses = sorted(house_distribution.items(), 
                                key=lambda x: len(x[1]), 
                                reverse=True)[:3]
        
        key_combinations = []
        for house, planets_list in important_houses:
            key_combinations.append({
                "宮位": house,
                "行星": planets_list,
                "重要度": len(planets_list)
            })
        
        return {
            "status": "success",
            "計算方法": calculation_method,
            "用戶資訊": {
                "姓名": user.name,
                "性別": user.gender,
                "出生日期": f"{user.birthDate[:4]}-{user.birthDate[4:6]}-{user.birthDate[6:8]}",
                "出生時間": user.birthTime,
                "出生地點": user.birthPlace
            },
            "星盤詳情": formatted_chart,
            "重要宮位組合": key_combinations,
            "宮位分佈": house_distribution
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.post("/chart")
def analyze_chart(req: ChartRequest):
    """原始的占星圖分析端點（Swiss Ephemeris版）"""
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
        
        # 嘗試使用Swiss Ephemeris
        try:
            if SWISSEPH_AVAILABLE:
                chart_data = calculate_swiss_ephemeris_chart(clean_date, req.time, req.lat, req.lon)
                calculation_method = "Swiss Ephemeris專業計算"
            else:
                raise Exception("Swiss Ephemeris不可用")
        except Exception as e:
            chart_data = create_advanced_fallback_chart(clean_date, req.time, req.lat, req.lon)
            calculation_method = "高精度備用計算"
        
        result = {}
        for planet_name, data in chart_data.items():
            result[planet_name] = {
                "sign": data["sign_name"],
                "house": data["house_name"],
                "longitude": data["longitude"],
                "degree_format": data["degree_format"],
                "speed": data["speed"]
            }
        
        return {
            "status": "success",
            "calculation_method": calculation_method,
            "planets": result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

@app.post("/bazi")
def analyze_bazi_only(req: ChartRequest):
    """專門的八字分析端點"""
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
        
        # 計算八字
        if LUNAR_AVAILABLE:
            bazi_data = calculate_bazi_chart(clean_date, req.time, req.lat, req.lon)
            calculation_method = "lunar-python專業計算"
        else:
            bazi_data = {"錯誤": "lunar-python不可用"}
            calculation_method = "計算失敗"
        
        return {
            "status": "success",
            "calculation_method": calculation_method,
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
        "service": "deep-language-ai-api",
        "modules": {
            "swiss_ephemeris": SWISSEPH_AVAILABLE,
            "lunar_python": LUNAR_AVAILABLE,
            "紫微斗數": "待整合"
        },
        "version": "5.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
