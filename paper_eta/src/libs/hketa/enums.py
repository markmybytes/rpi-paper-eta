from enum import Enum


class Locale(str, Enum):
    """Locale codes"""

    TC = "tc"
    EN = "en"

    def text(self) -> str:
        match self:
            case Locale.TC:
                return "繁體中文"
            case Locale.EN:
                return "English"

    def iso(self) -> str:
        match self:
            case Locale.TC:
                return "zh_HK"
            case Locale.EN:
                return "en_US"


class Company(str, Enum):
    """Enums representing different types of transport"""

    KMB = "kmb"
    MTRBUS = "mtr_bus"
    MTRLRT = "mtr_lrt"
    MTRTRAIN = "mtr_train"
    CTB = "ctb"
    NLB = "nlb"

    def text(self, language: Locale = Locale.TC) -> str:
        if language == Locale.EN:
            match self:
                case Company.KMB: return "KMB"
                case Company.MTRBUS: return "MTR (Bus)"
                case Company.MTRLRT: return "MTR (Light Rail)"
                case Company.MTRTRAIN: return "MTR"
                case Company.CTB: return "City Bus"
                case Company.NLB: return "New Lantao Bus"
        else:
            match self:
                case Company.KMB: return "九巴"
                case Company.MTRBUS: return "港鐵巴士"
                case Company.MTRLRT: return "輕鐵"
                case Company.MTRTRAIN: return "港鐵"
                case Company.CTB: return "城巴"
                case Company.NLB: return "新大嶼山巴士"


class Direction(str, Enum):
    """Direction of a route"""

    OUTBOUND = UPLINK = "outbound"
    INBOUND = DOWNLINK = "inbound"

    def text(self, language: Locale = Locale.TC) -> str:
        match language, self:
            case Locale.TC, Direction.OUTBOUND:
                return "去程"
            case Locale.TC, Direction.INBOUND:
                return "回程"
            case Locale.EN, Direction.OUTBOUND:
                return "Outbound"
            case Locale.EN, Direction.INBOUND:
                return "Inbound"


class StopType(str, Enum):
    """Type of a stop"""

    ORIG = ORIGINATION = "orig"
    STOP = MIDWAY = "stop"
    DEST = DESTINATION = "dest"

    def text(self, language: Locale = Locale.TC) -> "StopType":
        match language, self:
            case Locale.TC, StopType.ORIG | StopType.ORIGINATION:
                return "起點站"
            case Locale.TC, StopType.STOP | StopType.MIDWAY:
                return "中途站"
            case Locale.TC, StopType.DEST | StopType.DESTINATION:
                return "終點站"
            case Locale.EN, StopType.ORIG | StopType.ORIGINATION:
                return "Origination"
            case Locale.EN, StopType.STOP | StopType.MIDWAY:
                return "Midway Stop"
            case Locale.EN, StopType.DEST | StopType.DESTINATION:
                return "Destination"
