import calendar

cal = calendar.Calendar(firstweekday=6)

specs = {
    7: {'wd': '22/9', 'trad': [28, 29], 'sat_off': [4, 11, 18, 25, 27]},
    8: {'wd': '22/9', 'trad': [12], 'sat_off': [1, 8, 15, 22, 29]},
    9: {'wd': '22/8', 'trad': [], 'sat_off': [5, 12, 19, 26]},
    10: {'wd': '21/10', 'trad': [13, 23], 'sat_off': [3, 10, 12, 17, 24, 31]},
    11: {'wd': '23/7', 'trad': [], 'sat_off': [7, 14, 21, 28]},
    12: {'wd': '22/9', 'trad': [5, 31], 'sat_off': [12, 19, 26, 30]}
}

lines = ['  calendarMonths: Array<{ name: string; wd: string; weeks: Array<Array<{ d: number | null; t: string }>> }> = [']
for m in range(7, 13):
    m_name = calendar.month_name[m].upper()
    wd_val = specs[m]['wd']
    trad_list = specs[m]['trad']
    sat_list = specs[m]['sat_off']
    raw_weeks = cal.monthdayscalendar(2026, m)
    lines.append('    {')
    lines.append(f"      name: '{m_name}',")
    lines.append(f"      wd: '{wd_val}',")
    lines.append('      weeks: [')
    for w in raw_weeks:
        w_strs = []
        for col_idx, d in enumerate(w):
            if d == 0:
                w_strs.append("{ d: null, t: 'none' }")
            elif col_idx == 0:
                w_strs.append(f"{{ d: {d}, t: 'sun' }}")
            elif d in trad_list:
                w_strs.append(f"{{ d: {d}, t: 'trad' }}")
            elif d in sat_list:
                w_strs.append(f"{{ d: {d}, t: 'sat' }}")
            else:
                w_strs.append(f"{{ d: {d}, t: 'work' }}")
        lines.append('        [' + ', '.join(w_strs) + '],')
    lines.append('      ]')
    lines.append('    },')
lines.append('  ];')

lines.append('''
  calendarSummaryStats = [
    { value: '261', label: 'Working Day', boxClass: 'border border-emerald-600 text-emerald-800 bg-emerald-50' },
    { value: '15', label: 'Traditional Holiday', boxClass: 'bg-[#22c55e] text-white' },
    { value: '52', label: 'Holiday (sun)', boxClass: 'bg-red-500 text-white' },
    { value: '37', label: 'Holiday (sat)', boxClass: 'bg-[#facc15] text-slate-900' },
    { value: '104', label: 'Total Holiday', boxClass: 'border border-slate-400 text-slate-800 bg-white' }
  ];

  calendarHolidays = [
    { date: '28 July', title: "H.M. The King's Birthday" },
    { date: '29 July', title: 'Asanha Bucha Day' },
    { date: '12 August', title: "National Mother's Day" },
    { date: '13 October', title: 'Bhumibol Adulyadej Memorial Day' },
    { date: '23 October', title: 'Chulalongkorn Memorial Day' },
    { date: '5 December', title: "National Father's Day and National Day" },
    { date: '31 December', title: "New Year's eve" }
  ];

  calendarHospitalCols = [
    [
      { name: 'Thammasat University Hospital', phone: '0-2926-9999' },
      { name: 'Bumrungrad Hospital', phone: '0-2066-8888, 1378' },
      { name: 'Kasemrad Hospital Pathumthani', phone: '0-2529-4533' },
      { name: 'Karunvej Ayutthaya Hospital', phone: '0-3531-5100' },
      { name: 'Angthong Medical 2 Hospital', phone: '0-3561-2301-4' }
    ],
    [
      { name: 'Rajthanee Hospital', phone: '0-3533-5555-61' },
      { name: 'Navanakorn Hospital', phone: '0-2529-7888' },
      { name: 'Mitraparp Memorial Hospital', phone: '0-3621-8000' },
      { name: 'Phyathai 1 Hospital', phone: '0-2201-4600' },
      { name: 'Singburi Medical Hospital', phone: '0-3652-0517' }
    ],
    [
      { name: 'Benjarom Hospital', phone: '0-3641-3833' },
      { name: 'Ananda Mahidol Hospital', phone: '0-3678-5891' },
      { name: 'Vibhavadi Hospital', phone: '0-2561-1111' },
      { name: 'Phyathai 2 Hospital', phone: '0-2617-2444' },
      { name: 'Muangnarai Hospital', phone: '0-3642-0666' }
    ]
  ];
''')

with open('d:/suppier/cal_ts.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('cal_ts.txt written successfully')
