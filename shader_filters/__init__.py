from filter_one import FirstFilter
from filter_two import SecondFilter
from filter_three import ThirdFilter
from filter_rgb_shift import RGBShiftFilter
from filter_repeat_end import RepeatEndFilter
from filter_static import StaticFilter
from filter_static_2 import StaticFilter2
from filter_scanlines import ScanlineFilter
ALL_FILTERS = {'first': FirstFilter,
               'second': SecondFilter,
               'third': ThirdFilter,
               'rgb_shift': RGBShiftFilter,
               'repeat_end': RepeatEndFilter,
               'static': StaticFilter,
               'static2': StaticFilter2,
               'scanlines': ScanlineFilter}

# These are special shaders that probably won't work for filtering
from filter_ortho import OrthoFilter
from filter_console import ConsoleFilter
