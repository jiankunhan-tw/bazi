from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback
from typing import List, Optional
import uvicorn
import re
from datetime import date

app = FastAPI(
    title="全日期八字API",
    description="支援所有日期的八字計算系統",
    version="11.0.0"
)

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 嘗試導入 lunardate
try:
    from lunardate import LunarDate
    LUNARDATE_AVAILABLE = True
    print("lunardate農曆轉換庫已成功載入")
except ImportError:
    LUNARDATE_AVAILABLE = False
    print("lunardate不可用，使用備用計算")

# 天干地支
TIAN_GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
DI_ZHI   = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

# 納音表
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

# 十神對照表
SHI_SHEN_MAP = {
    "甲":{"甲":"比肩","乙":"劫財","丙":"食神","丁":"傷官","戊":"偏財","己":"正財","庚":"七殺","辛":"正官","壬":"偏印","癸":"正印"},
    "乙":{"甲":"劫財","乙":"比肩","丙":"傷官","丁":"食神","戊":"正財","己":"偏財","庚":"正官","辛":"七殺","壬":"正印","癸":"偏印"},
    "丙":{"甲":"偏印","乙":"正印","丙":"比肩","丁":"劫財","戊":"食神","己":"傷官","庚":"偏財","辛":"正財","壬":"七殺","癸":"正官"},
    "丁":{"甲":"正印","乙":"偏印","丙":"劫財","丁":"比肩","戊":"傷官","己":"食神","庚":"正財","辛":"偏財","壬":"正官","癸":"七殺"},
    "戊":{"甲":"七殺","乙":"正官","丙":"偏印","丁":"正印","戊":"比肩","己":"劫財","庚":"食神","辛":"傷官","壬":"偏財","癸":"正財"},
    "己":{"甲":"正官","乙":"七殺","丙":"正印","丁":"偏印","戊":"劫財","己":"比肩","庚":"傷官","辛":"食神","壬":"正財","癸":"偏財"},
    "庚":{"甲":"偏財","乙":"正財","丙":"七殺","丁":"正官","戊":"偏印","己":"正印","庚":"比肩","辛":"劫財","壬":"食神","癸":"傷官"},
    "辛":{"甲":"正財","乙":"偏財","丙":"正官","丁":"七殺","戊":"正印","己":"偏印","庚":"劫財","辛":"比肩","壬":"傷官","癸":"食神"},
    "壬":{"甲":"食神","乙":"傷官","丙":"偏財","丁":"正財","戊":"七殺","己":"正官","庚":"偏印","辛":"正印","壬":"比肩","癸":"劫財"},
    "癸":{"甲":"傷官","乙":"食神","丙":"正財","丁":"偏財","戊":"正官","己":"七殺","庚":"正印","辛":"偏印","壬":"劫財","癸":"比肩"}
}

# 地支藏干表
DIZHI_CANGAN = {
    "子":["癸"],"丑":["己","癸","辛"],"寅":["甲","丙","戊"],"卯":["乙"],"辰":["戊","乙","癸"],
    "巳":["丙","戊","庚"],"午":["丁","己"],"未":["己","丁","乙"],"申":["庚","壬","戊"],
    "酉":["辛"],"戌":["戊","辛","丁"],"亥":["壬","甲"]
}

# 五行對照表
WU_XING = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}


# ===================== 日柱/月柱/時柱（新版，無綁死） =====================

def _gregorian_to_serial(y, m, d):
    if m <= 2:
        y -= 1
        m += 12
    era = (y >= 0 and y) // 400
    yoe = y - era * 400
    doy = (153 * (m - 3) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe + 1

_BASE_RD_FOR_JIAZI = _gregorian_to_serial(1984, 2, 2)  # 1984-02-02 為甲子日

def get_day_ganzhi_from_gregorian(year, month, day):
    rd = _gregorian_to_serial(year, month, day)
    delta = rd - _BASE_RD_FOR_JIAZI
    gan = TIAN_GAN[delta % 10]
    zhi = DI_ZHI[delta % 12]
    return gan, zhi

_JIEQI_DAY = {1:6,2:4,3:6,4:5,5:6,6:6,7:7,8:8,9:8,10:8,11:7,12:7}

def get_year_ganzhi_solar(year, month, day):
    y = year if (month > 2 or (month == 2 and day >= _JIEQI_DAY[2])) else year - 1
    gan_index = (y - 1984) % 10
    zhi_index = (y - 1984) % 12
    return TIAN_GAN[gan_index], DI_ZHI[zhi_index]

def get_month_ganzhi_solar(year, month, day, year_gan):
    def _solar_month_index(y, m, d):
        if m == 1:
            idx = 12
        elif m == 2:
            idx = 1 if d >= _JIEQI_DAY[2] else 12
        else:
            base = 1
            delta = (m - 2)
            idx = ((base - 1 + delta) % 12) + 1
            if d < _JIEQI_DAY[m]:
                idx = 12 if idx == 1 else idx - 1
        return idx

    month_index = _solar_month_index(year, month, day)
    month_zhi_map = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]
    month_zhi = month_zhi_map[month_index - 1]

    yg_idx = TIAN_GAN.index(year_gan)
    month_gan_start = [2,4,6,8,0,2,4,6,8,0]
    gan_index = (month_gan_start[yg_idx] + (month_index - 1)) % 10
    month_gan = TIAN_GAN[gan_index]
    return month_gan, month_zhi

def get_hour_ganzhi_corrected(day_gan, hour, minute):
    if hour == 23 or hour == 0:
        zhi_index = 0
    else:
        zhi_index = (hour + 1) // 2
    hour_zhi = DI_ZHI[zhi_index]

    day_gan_index = TIAN_GAN.index(day_gan)
    hour_gan_base = [0,2,4,6,8,0,2,4,6,8]
    gan_index = (hour_gan_base[day_gan_index] + zhi_index) % 10
    hour_gan = TIAN_GAN[gan_index]
    return hour_gan, hour_zhi


# ========== 其他核心程式保持不動 ==========
# （這裡省略 parse_date_string、parse_time_string、calculate_comprehensive_bazi 等，
# 只要在呼叫的地方，換成：
# year_gan, year_zhi = get_year_ganzhi_solar(year, month, day)
# month_gan, month_zhi = get_month_ganzhi_solar(year, month, day, year_gan)
# day_gan, day_zhi   = get_day_ganzhi_from_gregorian(year, month, day)
# hour_gan, hour_zhi = get_hour_ganzhi_corrected(day_gan, hour, minute)
# 即可）
