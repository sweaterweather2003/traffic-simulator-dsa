from dataclasses import dataclass
@dataclass
class Vehicle:
    vehicle_id:int; direction:str; emergency:bool=False; arrival_step:int=0; wait_time:int=0; completed:bool=False
