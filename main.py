
import yaml
import sys
from omegaconf import DictConfig
import numpy as np
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

ReportTimeInterval = 30 # minutes
FIRST_HOUR_REPORT = 20
SECOND_HOUR_REPORT = 50

VALID_TYPES_OF_REPORT = ['METAR', 'MET1']
VALID_STATION_IDENTIFIER = ['LFSB', 'LSZB', 'LSGG', 'LSZG', 'LSGC', 'LSZA', 'LSZR', 'LSZH', 'LSZC', 'LSZS', 'LSGS', 'LSZG',
                            'LSMA', 'LSMD', 'LSME', 'LSMM', 'LSMP', 'LSZL', 'LSMO',
                            'LSMC']
VALID_VISIBILITY_DIRECTIONS = ['N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW']

@dataclass
class Wind:
    direction: int                          # in degrees
    force: int                              # in Knots
    direction_left: Optional [int] = None   # in degrees
    direction_right: Optional [int] = None  # in degrees
    gusts: Optional[int] = None             # in Knots
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.direction_left = np.mod(round(self.direction_left/10)*10,360)
        self.direction_right = np.mod(round(self.direction_right/10)*10,360)
        
        if (self.direction_left < self.direction and self.direction < self.direction_right):
            direction_mean = (self.direction_left + self.direction_right)/2
            direction_diff = self.direction_right - self.direction_left
        else:
            direction_mean = ((self.direction_left-360) + self.direction_right)/2
            direction_diff = self.direction_right - (self.direction_left-360)
            
        self.report_string = ""
        if (self.force == 0):
            self.direction = 0
            self.report_string += string_zero_padding(string=str(np.mod(round(self.direction/10)*10,360)), total_length=3)
            self.report_string += string_zero_padding(string=str(self.force), total_length=2)
            self.report_string += "KT"
        elif (self.force > 99 or self.gusts > 99):
            self.report_string += "P99"
        elif (60 <= direction_diff and direction_diff < 180 and self.force < 3) or direction_diff >= 180:
            self.report_string += "VRB" + string_zero_padding(string=str(self.force), total_length=2) + "KT"
        else:
            self.report_string += string_zero_padding(string=str(np.mod(round(self.direction/10)*10,360)), total_length=3)
            self.report_string += string_zero_padding(string=str(self.force), total_length=2)
            if (self.gusts >= self.force + 10):
                self.report_string += "G" + string_zero_padding(string=str(self.gusts), total_length=2)
            self.report_string += "KT"
            
            if (60 <= direction_diff and direction_diff < 180 and self.force >= 3):
                self.report_string += " " + string_zero_padding(string=str(self.direction_left), total_length=3) + "V" + string_zero_padding(string=str(self.direction_right), total_length=3)
    
def floor_visibility(dist: int) -> int:
    if (0 <= dist and dist < 800):
        dist = int(np.floor(dist/50)*50)
    elif (800 <= dist and dist < 5000):
        dist = int(np.floor(dist/100)*100)
    elif (5000 <= dist and dist < 10000):
        dist = int(np.floor(dist/1000)*1000)
    dist = np.minimum(dist, 9999)
    return dist

@dataclass
class Visibility:
    prevailing_distance: int                    # in meters
    smallest_distance: Optional[int] = None     # in meters
    smallest_direction: Optional[int] = None    # ['N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW']
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        if self.smallest_direction not in VALID_VISIBILITY_DIRECTIONS:
            raise Exception(self.smallest_direction + " is not a Valid Direction (N, S, E, W, NE, NW, SE, SW)!")
        
        self.report_string = ""
        
        self.prevailing_distance = floor_visibility(self.prevailing_distance)
        self.report_string += string_zero_padding(string=str(self.prevailing_distance), total_length=4)
        
        if ((self.smallest_distance < 1500) or \
            ((self.smallest_distance < 0.5*self.prevailing_distance) and \
            (self.smallest_distance < 5000))):
            
            self.smallest_distance = floor_visibility(self.smallest_distance)
            self.report_string += " " + str(string_zero_padding(string=str(self.smallest_distance), total_length=4)) + self.smallest_direction

def round_cloud_height(height: int) -> int:
    if (0 <= height and height < 10000):
        height = int(np.floor(height/100)*100)
    elif (10000 <= height and height < 43000):
        height = int(np.floor(height/1000)*1000)
    height = np.minimum(height, 43000)
    return height

@dataclass
class Clouds:
    cloud_list: list
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        lowest_cloud = 20000 # initialize at 20'000 ft above ground level (AAL)
        
        self.report_string = ""
        for c in self.cloud_list:
            self.report_string += c["crowd"] + \
                                  string_zero_padding(string=str(int(round_cloud_height(c["height"]*3.3)/100)), total_length=3) + \
                                  " "
            if (c["height"]*3.3 < lowest_cloud):
                lowest_cloud = round_cloud_height(c["height"]*3.3)
                
        # TODO NSC
        self.report_string += ""
        # TODO CAVOK
        self.report_string += ""
                                  
@dataclass
class Temperature_and_DewPoint:
    temperature: float
    dewPoint: float
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.report_string = ""
        if self.temperature < 0:
            self.report_string += "M" + string_zero_padding(str(abs(round(self.temperature))), total_length=2)
        else:
            self.report_string += string_zero_padding(string=str(round(self.temperature)), total_length=2)
        self.report_string += "/"
        if self.dewPoint < 0:
            self.report_string += "M" + string_zero_padding(str(abs(round(self.dewPoint))), total_length=2)
        else:
            self.report_string += string_zero_padding(string=str(round(self.dewPoint)), total_length=2)

@dataclass
class AirPressure:
    QFE: int
    cfg: DictConfig
    QNH: int = field(init=False)
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.QNH = self.QFE + round(self.cfg["defaults"]["Station_Altitude"]*3.3/30)
        self.report_string = "Q" + string_zero_padding(string=str(self.QNH), total_length=4)

def string_zero_padding(string: str, total_length: int) -> str:
    string = "0" * (total_length-len(string)) + string
    return string

def get_Date_and_Time() -> str:
    return string_zero_padding(string=str(datetime.now().year), total_length=4) + "-" + \
           string_zero_padding(string=str(datetime.now().month), total_length=2) + "-" + \
           string_zero_padding(string=str(datetime.now().day), total_length=2) + " " + \
           string_zero_padding(string=str(datetime.now().hour), total_length=2) + "h" + \
           string_zero_padding(string=str(datetime.now().minute), total_length=2) + "m" + \
           string_zero_padding(string=str(datetime.now().second), total_length=2) + "s"

def get_Type_of_Report(cfg: DictConfig) -> str:
    Type_of_Report = cfg['defaults']['Type_of_Report']
    if Type_of_Report not in VALID_TYPES_OF_REPORT:
        raise Exception(Type_of_Report + " is not a Valid Type of Report!")
    return Type_of_Report

def get_Station_Identifier(cfg: DictConfig) -> str:
    Station_Identifier = cfg['defaults']['Station_Identifier']
    if Station_Identifier not in VALID_STATION_IDENTIFIER:
        raise Exception(Station_Identifier + " is not a Valid Station Identifier!")
    return Station_Identifier

def get_UTC_Date_and_Time() -> str:
    minutes = datetime.now(timezone.utc).minute
    minutes = int((minutes>=FIRST_HOUR_REPORT-ReportTimeInterval/2) and (minutes<FIRST_HOUR_REPORT+ReportTimeInterval/2))*FIRST_HOUR_REPORT + \
              int(minutes>=SECOND_HOUR_REPORT-ReportTimeInterval/2 and minutes<SECOND_HOUR_REPORT+ReportTimeInterval/2)*SECOND_HOUR_REPORT
    return string_zero_padding(string=str(datetime.now(timezone.utc).day), total_length=2) + \
           string_zero_padding(string=str(datetime.now(timezone.utc).hour), total_length=2) + \
           string_zero_padding(string=str(minutes), total_length=2) + "Z"
    
def get_Modifier(source: str) -> str:
    if source == "AUTO":
        return source
    else:
        return ""

def get_Weather() -> str:
    # WMO Code tabelle
    return ""
 
def get_ColorCode(cfg: DictConfig, distance: int, cloud_list: list) -> str:
    lowest_height_above_ground = 20000 # 20'000 ft above ground level
    for c in cloud_list:
        if c["crowd"] == "BKN":
            height_above_ground = round((c["height"] - cfg["defaults"]["Station_Altitude"]) * 3.3)   # height above ground level in feet
            if (height_above_ground < lowest_height_above_ground): lowest_height_above_ground = height_above_ground

    if (distance == 0) or (lowest_height_above_ground == 0):
        s = "BLACK"
    elif (0 < distance and distance < 800) or \
         (0 < lowest_height_above_ground and lowest_height_above_ground < 200):
        s = "RED"
    elif (800 < distance and distance < 1600) or \
         (200 <= lowest_height_above_ground and lowest_height_above_ground < 300):
        s = "AMB"
    elif (1600 <= distance and distance < 3700) or \
         (300 <= lowest_height_above_ground and lowest_height_above_ground < 700):
        s = "YLO"
    elif (3700 <= distance and distance < 5000) or \
         (700 <= lowest_height_above_ground and lowest_height_above_ground < 1500):
        s = "GRN"
    elif (5000 <= distance and distance < 8000) or \
         (1500 <= lowest_height_above_ground and lowest_height_above_ground < 2500):
        s = "WHT"
    elif (distance == 8000) or (2500 <= lowest_height_above_ground and lowest_height_above_ground < 20000):
        s = "BLU"
    elif (8000 < distance) or (20000 <= lowest_height_above_ground):
        s = "BLU+"
    return s
    
def get_report_history(report: str) -> str:
    report_history = []
    report_history.append(report)
    return report_history

def get_report(cfg: DictConfig) -> str:
    
    wind = Wind(direction=cfg["METAR"]["Wind"]["direction"],
                force=cfg["METAR"]["Wind"]["force"],
                direction_left=cfg["METAR"]["Wind"]["direction_left"],
                direction_right=cfg["METAR"]["Wind"]["direction_right"],
                gusts=cfg["METAR"]["Wind"]["gusts"])
    
    visibility = Visibility(prevailing_distance=cfg["METAR"]["Visibility"]["prevailing_distance"],
                            smallest_distance=cfg["METAR"]["Visibility"]["smallest_distance"],
                            smallest_direction=cfg["METAR"]["Visibility"]["smallest_direction"])
    
    c = [{"crowd": "FEW", "height": 1000},
    {"crowd": "SCT", "height": 2000},
    {"crowd": "BKN", "height": 4000}]
    
    print(c)

    clouds = Clouds(cloud_list=[{"crowd": "FEW", "height": 1000},
                                {"crowd": "SCT", "height": 2000},
                                {"crowd": "BKN", "height": 4000}])
    temperature_and_dewPoint = Temperature_and_DewPoint(temperature=cfg["METAR"]["Temperature_and_DewPoint"]["temperature"],
                                                        dewPoint=cfg["METAR"]["Temperature_and_DewPoint"]["dewPoint"])
    airPressure = AirPressure(QFE=cfg["METAR"]["AirPressure"]["QFE"], cfg=cfg)
    
    report = ""
    report += get_Type_of_Report(cfg) + " "
    report += get_Station_Identifier(cfg) + " "
    report += get_UTC_Date_and_Time() + " "
    report += get_Modifier(source="") + " "
    report += wind.report_string + " "
    report += visibility.report_string + " "
    report += get_Weather() + " "
    report += clouds.report_string + " "
    report += temperature_and_dewPoint.report_string + " "
    report += airPressure.report_string + " "
    report += get_ColorCode(cfg, visibility.prevailing_distance, clouds.cloud_list)

    return report

def main(cfg: DictConfig, save_report_history: bool) -> None:
    report = get_report_history(cfg)
    report = get_report(cfg)
    print(report)
    
    # Compute Report History
    if save_report_history:
        text_file = open("report_history.txt", "a")
        text_file.write(get_Date_and_Time() + ": " + report + "\n")
        text_file.close()

if __name__ == '__main__':
    # Load Default Report Configuration File
    cfg = yaml.safe_load(open("config/default_Report.yaml"))
    # Run Report Computation
    main(cfg, save_report_history=True)

    