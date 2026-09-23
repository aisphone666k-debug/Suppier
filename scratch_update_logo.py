import base64
import re

with open('d:/suppier/public/minebea-transparent-logo.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

new_data_url = 'data:image/png;base64,' + b64

with open('d:/suppier/src/app/app.component.ts', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r"calendarLogoDataUrl = 'data:image/png;base64,[^']+';"
if re.search(pattern, content):
    content = re.sub(pattern, f"calendarLogoDataUrl = '{new_data_url}';", content)
    with open('d:/suppier/src/app/app.component.ts', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Updated calendarLogoDataUrl with transparent logo!')
else:
    print('ERROR: Pattern not matched')
