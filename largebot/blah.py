from pathlib import Path
import pandas as pd

media_xl = Path.home() / 'Downloads' / 'MediaCable Testing.xlsx'
df = pd.read_excel(media_xl, sheet_name='Scripts')