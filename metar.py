
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
VALID_VISIBILITY_DIRECTIONS = ['N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', "", None]
VALID_CROWD = ['FEW', 'SCT', 'BKN', 'OVC']
VALID_THUNDERCLOUDS = ['TCU', 'CB']

@dataclass
class Wind:
    force: int                              # in Knots
    direction_left: int = None              # in degrees
    direction_right: int = None             # in degrees
    gusts: Optional[int] = None             # in Knots
    direction_mean: int = field(init=False)
    direction_diff: int = field(init=False)
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.direction_left = np.mod(round(float(self.direction_left)/10)*10,360)
        self.direction_right = np.mod(round(self.direction_right/10)*10,360)
        
        if (self.direction_left <= self.direction_right):
            self.direction_mean = round(((self.direction_left + self.direction_right)/2)/10)*10
            self.direction_diff = self.direction_right - self.direction_left
        else:
            self.direction_mean = round((((self.direction_left-360) + self.direction_right)/2)/10)*10
            self.direction_diff = self.direction_right - (self.direction_left-360)
            
        self.report_string = " "
        if (self.force == 0):
            self.direction_mean = 0
            self.report_string += string_zero_padding(string=str(np.mod(round(self.direction_mean/10)*10,360)), total_length=3)
            self.report_string += string_zero_padding(string=str(self.force), total_length=2)
            self.report_string += "KT"
        elif (self.force > 99 or (self.gusts is not None and self.gusts > 99)):
            self.report_string += "P99"
        elif (60 <= self.direction_diff and self.direction_diff < 180 and self.force < 3) or self.direction_diff >= 180:
            self.report_string += "VRB" + string_zero_padding(string=str(self.force), total_length=2) + "KT"
        else:
            self.report_string += string_zero_padding(string=str(np.mod(round(self.direction_mean/10)*10,360)), total_length=3)
            self.report_string += string_zero_padding(string=str(self.force), total_length=2)
            if ((self.gusts is not None) and (self.gusts >= self.force + 10)):
                self.report_string += "G" + string_zero_padding(string=str(self.gusts), total_length=2)
            self.report_string += "KT"
            
            if (60 <= self.direction_diff and self.direction_diff < 180 and self.force >= 3):
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
        self.report_string = " "
        
        if (self.prevailing_distance is not None):
            self.report_string += string_zero_padding(string=str(floor_visibility(self.prevailing_distance)), total_length=4)
        
        if ((self.smallest_distance is not None) and (self.smallest_direction != "") and \
            ((self.smallest_distance < 1500) or \
            ((self.smallest_distance < 0.5*floor_visibility(self.prevailing_distance)) and \
            (self.smallest_distance < 5000)))):
            
            self.report_string += " " + str(string_zero_padding(string=str(floor_visibility(self.smallest_distance)), total_length=4)) + self.smallest_direction
                
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
    lowest_cloud: int = field(init=False)                # in ft
    thunderclouds_available: bool = field(init=False)
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.lowest_cloud = 20000 # initialize at 20'000 ft above ground level (AAL)
        self.thunderclouds_available = False
        for c in self.cloud_list:
            if c["crowd"] in VALID_CROWD:
                if (c["height"]*3.3 < self.lowest_cloud):
                    self.lowest_cloud = round_cloud_height(c["height"]*3.3)
                if c["thundercloud"] in ["TCU", "CB"]:
                    self.thunderclouds_available = True
                    
        self.report_string = ""
        for c in self.cloud_list:
            if c["crowd"] in VALID_CROWD:
                self.report_string += " " + c["crowd"] + \
                                    string_zero_padding(string=str(int(round_cloud_height(c["height"]*3.3)/100)), total_length=3)
                                    
                if c["thundercloud"] in VALID_THUNDERCLOUDS:
                    self.report_string += c["thundercloud"]
                                    
        # TODO NSC
        self.report_string += ""
                                                  
@dataclass
class Temperature_and_DewPoint:
    dry_temperature: float
    wet_temperature: float
    airPressure: int
    dewPoint: float = field(init=False)
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.report_string = ""
        if (self.dry_temperature is not None and self.wet_temperature is not None):
            # calculate dewPoint
            saturated_vapor_pressure_dry = 6.108*np.exp(17.27*self.dry_temperature/(237.3+self.dry_temperature))
            saturated_vapor_pressure_wet = 6.108*np.exp(17.27*self.wet_temperature/(237.3+self.wet_temperature))
            vapor_pressure_water = saturated_vapor_pressure_wet - 0.00066*(1+0.00115*self.wet_temperature)*(self.dry_temperature-self.wet_temperature)*self.airPressure
            z = np.log(vapor_pressure_water/6.108)/17.27
            self.dewPoint = 237.3*z/(1-z)
            
            # TODO limit log
            
            self.report_string += " "
                    
            if self.dry_temperature < 0:
                self.report_string += "M" + string_zero_padding(str(abs(round(self.dry_temperature))), total_length=2)
            else:
                self.report_string += string_zero_padding(string=str(round(self.dry_temperature)), total_length=2)
            self.report_string += "/"
            if self.dewPoint < 0:
                self.report_string += "M" + string_zero_padding(str(abs(round(self.dewPoint))), total_length=2)
            else:
                self.report_string += string_zero_padding(string=str(round(self.dewPoint)), total_length=2)
                
@dataclass
class AirPressure:
    QFE: int
    station_altitude: int
    QNH: int = field(init=False)
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.report_string = ""
        if (self.QFE is not None and self.station_altitude is not None):
            self.QNH = self.QFE + round(self.station_altitude*3.3/30)
            self.report_string += " Q" + string_zero_padding(string=str(self.QNH), total_length=4)
                
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

@dataclass
class Report:
    type: str
    report_type: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.report_type = ""
        if self.type in VALID_TYPES_OF_REPORT:
            self.report_type += self.type

@dataclass
class Station:
    identifier: str
    altitude: int
    report_identifier: str = field(init=False)
    
    def __post_init__(self) -> None:
        # station identifier
        self.report_identifier = ""
        if self.identifier in VALID_STATION_IDENTIFIER:
            self.report_identifier  += " " + self.identifier
            
            

def get_UTC_Date_and_Time() -> str:
    minutes = datetime.now(timezone.utc).minute
    minutes = int((minutes>=(FIRST_HOUR_REPORT-ReportTimeInterval/2)%60) and (minutes<(FIRST_HOUR_REPORT+ReportTimeInterval/2))%60)*FIRST_HOUR_REPORT + \
              int((minutes>=(SECOND_HOUR_REPORT-ReportTimeInterval/2)%60) or (minutes<(SECOND_HOUR_REPORT+ReportTimeInterval/2)%60))*SECOND_HOUR_REPORT
    return " " + \
           string_zero_padding(string=str(datetime.now(timezone.utc).day), total_length=2) + \
           string_zero_padding(string=str(datetime.now(timezone.utc).hour), total_length=2) + \
           string_zero_padding(string=str(minutes), total_length=2) + \
           "Z"
    

@dataclass
class Weather:
    weather_phenomena: str
    no_phenomena: bool = field(init=False)
    report_string: str = field(init=False)
    
    def __post_init__(self) -> None:
        self.no_phenomena = False
        if self.weather_phenomena == "":
            self.no_phenomena = True
            
        self.report_string = ""
        if not self.no_phenomena:
            self.report_string += " "
            self.report_string += self.weather_phenomena
 
def get_ColorCode(station_altitude: int, distance: int, cloud_list: list) -> str:
    lowest_height_above_ground = 20000 # 20'000 ft above ground level
    s = " "
    for c in cloud_list:
        if ((c["crowd"] == "BKN") or (c["crowd"] == "BKN")):
            height_above_ground = round((c["height"] - station_altitude) * 3.3)   # height above ground level in feet
            if (height_above_ground < lowest_height_above_ground): lowest_height_above_ground = height_above_ground

    if ((distance is not None) and (distance == 0)) or ((lowest_height_above_ground is not None) and (lowest_height_above_ground == 0)):
        s += "BLACK"
    elif ((distance is not None) and (0 < distance and distance < 800)) or \
         ((lowest_height_above_ground is not None) and (0 < lowest_height_above_ground and lowest_height_above_ground < 200)):
        s += "RED"
    elif ((distance is not None) and (800 < distance and distance < 1600)) or \
         ((lowest_height_above_ground is not None) and (200 <= lowest_height_above_ground and lowest_height_above_ground < 300)):
        s += "AMB"
    elif ((distance is not None) and (1600 <= distance and distance < 3700)) or \
         ((lowest_height_above_ground is not None) and (300 <= lowest_height_above_ground and lowest_height_above_ground < 700)):
        s += "YLO"
    elif ((distance is not None) and (3700 <= distance and distance < 5000)) or \
         ((lowest_height_above_ground is not None) and (700 <= lowest_height_above_ground and lowest_height_above_ground < 1500)):
        s += "GRN"
    elif ((distance is not None) and (5000 <= distance and distance < 8000)) or \
         ((lowest_height_above_ground is not None) and (1500 <= lowest_height_above_ground and lowest_height_above_ground < 2500)):
        s += "WHT"
    elif ((distance is not None) and (distance == 8000)) or \
         ((lowest_height_above_ground is not None) and (2500 <= lowest_height_above_ground and lowest_height_above_ground < 20000)):
        s += "BLU"
    elif ((distance is not None) and (8000 < distance)) or \
         ((lowest_height_above_ground is not None) and (20000 <= lowest_height_above_ground)):
        s += "BLU+"
        
    return s

def get_report_from_gui(type_of_report, station_identifier, station_altitude,
                        force, direction_left, direction_right, gusts,
                        prevailing_distance, smallest_distance, smallest_direction,
                        weather_phenomena,
                        cloud_list,
                        dry_temperature, wet_temperature,
                        QFE
                        ) -> str:
    
    report = Report(type=type_of_report)
    station = Station(identifier=station_identifier, altitude=station_altitude)
    wind = Wind(force=force, direction_left=direction_left, direction_right=direction_right, gusts=gusts)
    visibility = Visibility(prevailing_distance=prevailing_distance, smallest_distance=smallest_distance, smallest_direction=smallest_direction)
    weather = Weather(weather_phenomena=weather_phenomena)
    clouds = Clouds(cloud_list=cloud_list)
    airPressure = AirPressure(QFE=QFE, station_altitude=station.altitude)
    temperature_and_dewPoint = Temperature_and_DewPoint(dry_temperature=dry_temperature, wet_temperature=wet_temperature, airPressure=airPressure.QFE)

    #TODO put blank space in each function instead 
    
    report_string = ""
    report_string += report.report_type
    report_string += station.report_identifier
    report_string += get_UTC_Date_and_Time()
    report_string += wind.report_string
        
    # CAVOK?
    if (visibility.prevailing_distance >= 10000 and \
        clouds.lowest_cloud >= 5000 and \
        not clouds.thunderclouds_available and \
        weather.no_phenomena
        ):
        report_string += " CAVOK"
    else:
        report_string += visibility.report_string
        report_string += weather.report_string
        report_string += clouds.report_string
    
    report_string += temperature_and_dewPoint.report_string
    report_string += airPressure.report_string
    report_string += get_ColorCode(station.altitude, visibility.prevailing_distance, clouds.cloud_list)

    return report_string

if __name__ == '__main__':
    # Load Default Report Configuration File
    cfg = yaml.safe_load(open("config/default_Report.yaml"))
    
    # Run Report Computation
    save_report_history = False
    report = get_report_from_gui(type_of_report="METAR", station_identifier="LSMC", station_altitude=564,
                                 force=4, direction_left=10, direction_right=80, gusts=None,
                                 prevailing_distance=10000, smallest_distance=3000, smallest_direction="SW",
                                 weather_phenomena="",
                                 cloud_list=[{"crowd": "FEW", "height": 1000, "thundercloud": ""},{"crowd": "SCT", "height": 2000, "thundercloud": ""},{"crowd": "BKN", "height": 4000, "thundercloud": ""}],
                                 dry_temperature=1.3, wet_temperature=-1.5,
                                 QFE=949)
    print(report)
    
    # Compute Report History
    if save_report_history:
        text_file = open("report_history.txt", "a")
        text_file.write(get_Date_and_Time() + ": " + report + "\n")
        text_file.close()

    