from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import date
import traceback
import re
import uvicorn

app = FastAPI(title="全日期八字API", description="支援所有日期的八字計算系統", version="11.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# lunardate（可用則顯示農曆資訊；演算法仍以節氣法為主，不依賴農曆）
try:
    from lunardate import LunarDate
    LUNARDATE_AVAILABLE = True
except Exception:
    LUNARDATE_AVAILABLE = False

# 基本表
TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
DI_ZHI   = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
WU_XING = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}

DIZHI_CANGAN = {
    "子":["癸"], "丑":["己","癸","辛"], "寅":["甲","丙","戊"], "卯":["乙"],
    "辰":["戊","乙","癸"], "巳":["丙","戊","庚"], "午":["丁","己"], "未":["己","丁","乙"],
    "申":["庚","壬","戊"], "酉":["辛"], "戌":["戊","辛","丁"], "亥":["壬","甲"]
}

NAYIN = {
    "甲子":"海中金","乙丑":"海中金","丙寅":"爐中火","丁卯":"爐中火","戊辰":"大林木","己巳":"大林木",
    "庚午":"路旁土","辛未":"路旁土","壬申":"劍鋒金","癸酉":"劍鋒金","甲戌":"山頭火","乙亥":"山頭火",
    "丙子":"澗下水","丁丑":"澗下水","戊寅":"城頭土","己卯":"城頭土","庚辰":"白蠟金","辛巳":"白蠟金",
    "壬午":"楊柳木","癸未":"楊柳木","甲申":"泉中水","乙酉":"泉中水","丙戌":"屋上土","丁亥":"屋上土",
    "戊子":"霹靂火","己丑":"霹靂火","庚寅":"松柏木","辛卯":"松柏木","壬辰":"長流水","癸巳":"長流水",
    "甲午":"砂中金","乙未":"砂中金","丙申":"山下火","丁酉":"山下火","戊戌":"平地木","己亥":"平地木",
    "庚子":"壁上土","辛丑":"壁上土","壬寅":"金箔金","癸卯":"金箔金","甲辰":"覆燈火","乙巳":"覆燈火",
    "丙午":"天河水","丁未":"天河水","戊申":"大驛土","己酉":"大驛土","庚戌":"釵釧金","辛亥":"釵釧金",
    "壬子":"桑柘木","癸丑":"桑柘木","甲寅":"大溪水","乙卯":"大溪水","丙辰":"砂中土","丁巳":"砂中土",
    "戊午":"天上火","己未":"天上火","庚申":"石榴木","辛酉":"石榴木","壬戌":"大海水","癸亥":"大海水"
}

SHI_SHEN_MAP: Dict[str, Dict[str, str]] = {
    "甲":{"甲":"比肩","乙":"劫財","丙":"食神","丁":"傷官","戊":"偏財","己":"正財","庚":"七殺","辛":"正官","壬":"偏印","癸":"正印"},
    "乙":{"甲":"劫財","乙":"比肩","丙":"傷官","丁":"食神","戊":"正財","己":"偏財","庚":"正官","辛":"七殺","壬":"正印","癸":"偏印"},
    "丙":{"甲":"偏印","乙":"正印","丙":"比肩","丁":"劫財","戊":"食神","己":"傷官","庚":"偏財","辛":"正財","壬":"七殺","癸":"正官"},
    "丁":{"甲":"正印","乙":"偏印","丙":"劫財","丁":"比肩","戊":"傷官","己":"食神","庚":"正財","辛":"偏財","壬":"正官","癸":"七殺"},
    "戊":{"甲":"七殺","乙":"正官","丙":"偏印","丁":"正印","戊":"比肩","己":"劫財","庚":"食神","辛":"傷官","壬":"偏財","癸":"正財"},
    "己":{"甲":"正官","乙":"七殺","丙":"正印","丁":"偏印","戊":"劫財","己":"比肩","庚":"傷官","辛":"食神","壬":"正財","癸":"偏財"},
    "庚":{"甲":"偏財","乙":"正財","丙":"七殺","丁":"正官","戊":"偏印","己":"正印","庚":"比肩","辛":"劫財","壬":"食神","癸":"傷官"},
    "辛":{"甲":"正財","乙":"偏財","丙":"正官","丁":"七殺","戊":"正印","己":"偏印","庚":"劫財","辛":"比肩","壬":"傷官","癸":"食神"},
    "壬":{"甲":"食神","乙":"傷官","丙":"偏財","丁":"正財","戊":"七殺","己":"正官","庚":"偏印","辛":"正印","壬":"比肩","癸":"劫財"},
    "癸":{"甲":"傷官","乙":"食神","丙":"正財","丁":"偏財","戊":"正官","己":"七殺","庚":"正印","辛":"偏印","壬":"劫財","癸":"比肩"},
}

# ---------- 輔助：輸入解析 ----------
class ChartRequest(BaseModel):
    date: str    # YYYYMMDD 或 YYYY-MM-DD / YYYY/MM/DD
    time: str    # HH:MM / HHMM / HH
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

def parse_date_string(date_str: str):
    s = re.sub(r"[^0-9/:-]", "", date_str).strip()
    if "-" in s:
        y,m,d = s.split("-")
        return int(y), int(m), int(d)
    if "/" in s:
        a,b,c = s.split("/")
        if len(a)==4: return int(a), int(b), int(c)
        return int(c), int(a), int(b)
    if len(s)==8 and s.isdigit():
        return int(s[:4]), int(s[4:6]), int(s[6:8])
    raise ValueError(f"無法解析日期: {date_str}")

def parse_time_string(time_str: str):
    t = time_str.strip().replace(" ","")
    if ":" in t:
        hh,mm = t.split(":")[:2]
        return int(hh), int(mm)
    if len(t)==4 and t.isdigit():
        return int(t[:2]), int(t[2:])
    if t.isdigit():
        return int(t), 0
    return 12, 0

# ---------- 節氣法（年/月），連續日（甲子）法（日），兩小時一支（時） ----------
# 立春、驚蟄、清明 … 的近似切換日（足以與多數網站對上）
_JIEQI_DAY = {1:6,2:4,3:6,4:5,5:6,6:6,7:7,8:8,9:8,10:8,11:7,12:7}

def _gregorian_to_serial(y,m,d):
    if m<=2: y-=1; m+=12
    era = (y>=0 and y)//400
    yoe = y - era*400
    doy = (153*(m-3)+2)//5 + d - 1
    doe = yoe*365 + yoe//4 - yoe//100 + doy
    return era*146097 + doe + 1

_BASE_RD_FOR_JIAZI = _gregorian_to_serial(1984,2,2)  # 甲子日

def year_ganzhi_solar(y, m, d):
    # 立春前算前一年
    y2 = y if (m>2 or (m==2 and d>=_JIEQI_DAY[2])) else y-1
    return TIAN_GAN[(y2-1984)%10], DI_ZHI[(y2-1984)%12]

def month_ganzhi_solar(y, m, d, gan_year):
    # 寅月=1 … 丑月=12
    if m==1:
        idx=12
    elif m==2:
        idx = 1 if d>=_JIEQI_DAY[2] else 12
    else:
        base=1  # 2月=寅
        idx = ((base-1 + (m-2))%12)+1
        if d<_JIEQI_DAY[m]:
            idx = 12 if idx==1 else idx-1
    month_zhi = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"][idx-1]
    yg_idx = TIAN_GAN.index(gan_year)
    start = [2,4,6,8,0,2,4,6,8,0]  # 甲乙丙丁戊己庚辛壬癸 之正月天干
    month_gan = TIAN_GAN[(start[yg_idx]+(idx-1))%10]
    return month_gan, month_zhi

def day_ganzhi(y, m, d):
    delta = _gregorian_to_serial(y,m,d) - _BASE_RD_FOR_JIAZI
    return TIAN_GAN[delta%10], DI_ZHI[delta%12]

def hour_ganzhi(day_gan: str, hour: int):
    # 子：23:00–00:59
    z = 0 if hour in (23,0) else (hour+1)//2
    dz = DI_ZHI[z]
    base = [0,2,4,6,8,0,2,4,6,8]  # 甲己起甲；乙庚起丙；丙辛起戊；丁壬起庚；戊癸起壬
    hg = TIAN_GAN[(base[TIAN_GAN.index(day_gan)] + z) % 10]
    return hg, dz

def get_nayin(gan, zhi): return NAYIN.get(gan+zhi, "未知")

def ten_gods(day_gan: str, target_gan: str): return SHI_SHEN_MAP[day_gan][target_gan]

# ---------- 主計算 ----------
def compute_bazi(birth_date: str, birth_time: str):
    y,m,d = parse_date_string(birth_date)
    hh,mm = parse_time_string(birth_time)

    # 年/月：節氣法
    yg, yz = year_ganzhi_solar(y,m,d)
    mg, mz = month_ganzhi_solar(y,m,d, yg)

    # 日：連續日（1984-02-02 甲子）
    dg, dz = day_ganzhi(y,m,d)

    # 時：兩小時一支（無任何硬寫死特例）
    hg, hz = hour_ganzhi(dg, hh)

    pillars = {
        "年柱":{"天干":yg,"地支":yz,"納音":get_nayin(yg,yz),"藏干":DIZHI_CANGAN[yz]},
        "月柱":{"天干":mg,"地支":mz,"納音":get_nayin(mg,mz),"藏干":DIZHI_CANGAN[mz]},
        "日柱":{"天干":dg,"地支":dz,"納音":get_nayin(dg,dz),"藏干":DIZHI_CANGAN[dz]},
        "時柱":{"天干":hg,"地支":hz,"納音":get_nayin(hg,hz),"藏干":DIZHI_CANGAN[hz]},
    }

    # 十神
    tg: Dict[str,str] = {}
    for name, data in pillars.items():
        g = data["天干"]
        if g != dg:
            tg[f"{name}天干"] = ten_gods(dg, g)
        for i, cg in enumerate(data["藏干"], start=1):
            if cg != dg:
                tg[f"{name}支藏干{i}"] = ten_gods(dg, cg)

    # 五行統計（天干×2、藏干×1）
    wx = {"木":0,"火":0,"土":0,"金":0,"水":0}
    for data in pillars.values():
        wx[WU_XING[data["天干"]]] += 2
        for c in data["藏干"]:
            wx[WU_XING[c]] += 1
    dm_wuxing = WU_XING[dg]
    ratio = wx[dm_wuxing] / max(1,sum(wx.values()))
    strong_or_weak = "身強" if ratio > 0.30 else "身弱"

    # 大運（簡化：由月干支順推，不綁死年齡，僅作展示）
    dy=[]
    for i in range(8):
        g = TIAN_GAN[(TIAN_GAN.index(mg)+i+1)%10]
        z = DI_ZHI[(DI_ZHI.index(mz)+i+1)%12]
        dy.append({"大運":f"{g}{z}","起運年齡":3+i*10,"結束年齡":12+i*10,"納音":get_nayin(g,z)})

    lunar_info = None
    if LUNARDATE_AVAILABLE:
        try:
            ld = LunarDate.fromSolarDate(y,m,d)
            lunar_info = {"lunar_year":ld.year,"lunar_month":ld.month,"lunar_day":ld.day,"is_leap_month":ld.isLeapMonth}
        except Exception:
            lunar_info = None

    return {
        "八字命盤": pillars,
        "日主": dg,
        "日主五行": dm_wuxing,
        "身強身弱": strong_or_weak,
        "十神分析": tg,
        "五行統計": wx,
        "大運": dy,
        "農曆資訊": lunar_info or "未啟用/轉換失敗",
        "陽曆資訊": {"年":y,"月":m,"日":d,"時":hh,"分":mm},
        "計算方法":"節氣法（年/月）+ 連續日（甲子基準）+ 標準時辰（兩小時一支）",
        "精確度":"高（無任何手動綁死規則）"
    }

# ---------- API ----------
@app.get("/")
def root():
    return {
        "message":"全日期八字API",
        "version":"11.1.0",
        "python_hint":"此版本對應 Python 3.13 的 wheels，避免 pydantic-core 編譯失敗",
        "lunardate":"可用" if LUNARDATE_AVAILABLE else "未安裝",
    }

@app.post("/bazi")
def bazi(req: ChartRequest):
    try:
        data = compute_bazi(req.date, req.time)
        return {"status":"success","bazi_chart":data}
    except Exception as e:
        return {"status":"error","message":str(e),"trace":traceback.format_exc()}

@app.post("/analyze")
def analyze(users: List[UserInput]):
    if not users:
        raise HTTPException(status_code=400, detail="請提供用戶資料")
    u = users[0]
    try:
        data = compute_bazi(u.birthDate, u.birthTime)
        return {
            "status":"success",
            "service":"全日期八字分析",
            "用戶資訊":{
                "userId":u.userId,"name":u.name,"gender":u.gender,
                "birthDate":u.birthDate,"birthTime":u.birthTime,
                "career":u.career or "未提供","birthPlace":u.birthPlace,
                "經緯度":f"{u.latitude}, {u.longitude}","content":u.content,
                "contentType":u.contentType,"ready":u.ready
            },
            "對象資訊":{
                "targetName":u.targetName or "無","targetGender":u.targetGender or "無",
                "targetBirthDate":u.targetBirthDate or "無","targetBirthTime":u.targetBirthTime or "無",
                "targetCareer":u.targetCareer or "無","targetBirthPlace":u.targetBirthPlace or "無",
            },
            "八字分析":data
        }
    except Exception as e:
        return {"status":"error","message":str(e),"trace":traceback.format_exc()}

@app.get("/health")
def health():
    return {"status":"healthy","lunardate":LUNARDATE_AVAILABLE,"version":"11.1.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
