import json
import os

os.makedirs('Parsed_Responses', exist_ok=True)

models_data = {
    "ChatGPT": [
        {"Hospital": "Arnprior Regional Health", "Issue": "Interim President & CEO appointed — Pierre Noel", "Paragraph blurb": "", "Date": "July 13, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "President & CEO transition — Carmine Stumpo", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "Vice President, People Services & Chief Human Resources Officer — Stav D’Andrea retirement", "Paragraph blurb": "", "Date": "February 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Appointment of Serda Evren as Chief Communications", "Paragraph blurb": "", "Date": "January 26, 2026", "Source": "North York General", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Appointment of Simone Atungo as Board Governor", "Paragraph blurb": "", "Date": "July 3, 2026", "Source": "North York General", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Appointment of Dr. Kathryn Nichol as Board Governor", "Paragraph blurb": "", "Date": "July 3, 2026", "Source": "North York General", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Dr. Manish Shah assumes President, Medical Staff Association", "Paragraph blurb": "", "Date": "July 2026", "Source": "North York General", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}}
    ],
    "Claude": [
        {"Hospital": "Arnprior Regional Health", "Issue": "President & CEO departure — Jeremy Stevenson", "Paragraph blurb": "", "Date": "June 2, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "Acting President & CEO — Raeline McGrath", "Paragraph blurb": "", "Date": "June 2, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "Interim President & CEO appointment — Pierre Noel", "Paragraph blurb": "", "Date": "July 13, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "New Board Directors — Dr. Matthew Dick, Katrina Roberts, Bill Stevens", "Paragraph blurb": "", "Date": "June 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "President & CEO transition — Carmine Stumpo", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Board of Governors recruitment drive", "Paragraph blurb": "", "Date": "February 24, 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Medical Staff Association Presidency transition - Dr. Shah", "Paragraph blurb": "", "Date": "July 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}}
    ],
    "Gemini": [
        {"Hospital": "Arnprior Regional Health", "Issue": "President & CEO Resignation - Jeremy Stevenson", "Paragraph blurb": "", "Date": "June 2, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "Acting President & CEO Appointment - Raeline McGrath", "Paragraph blurb": "", "Date": "June 2, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "Interim President & CEO Appointment - Pierre Noel", "Paragraph blurb": "", "Date": "July 13, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "CEO Appointment and Transition - Carmine Stumpo", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Chief Communications Officer Transition - Serda Evren", "Paragraph blurb": "", "Date": "January 26, 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Board of Governors Recruitment", "Paragraph blurb": "", "Date": "February 24, 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}}
    ],
    "Perplexity": [
        {"Hospital": "Arnprior Regional Health", "Issue": "President and CEO departure — Jeremy Stevenson", "Paragraph blurb": "", "Date": "June 2, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "Acting President and CEO — Raeline McGrath", "Paragraph blurb": "", "Date": "June 2, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "Interim President and CEO appointment — Pierre Noel", "Paragraph blurb": "", "Date": "July 13, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "President & CEO appointment - Carmine Stumpo", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "Board succession / recruitment", "Paragraph blurb": "", "Date": "June 22, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Chief Communications and External Relations Officer - Serda Evren", "Paragraph blurb": "", "Date": "January 26, 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Board renewal / recruitment — two Board Governors", "Paragraph blurb": "", "Date": "February 24, 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}}
    ],
    "MS Copilot Agent": [
        {"Hospital": "Arnprior Regional Health", "Issue": "Interim President and CEO appointed - Pierre Noel", "Paragraph blurb": "", "Date": "July 13, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "Acting President and CEO assignment concluded - Raeline McGrath", "Paragraph blurb": "", "Date": "July 13, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Arnprior Regional Health", "Issue": "President and CEO departure - Jeremy Stevenson", "Paragraph blurb": "", "Date": "June 2, 2026", "Source": "Arnprior Regional Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "President and CEO transition - Carmine Stumpo", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "End of interim President and CEO assignment - Mary-Agnes Wilson", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "Interim Chief Human Resources Officer coverage - Marissa Salmon", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "Interim oversight of People Services - David Stolte", "Paragraph blurb": "", "Date": "April 13, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "Mackenzie Health", "Issue": "Board election and reappointment process", "Paragraph blurb": "", "Date": "May 28, 2026", "Source": "Mackenzie Health", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Chief Communications and External Relations Officer - Serda Evren", "Paragraph blurb": "", "Date": "January 26, 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}},
        {"Hospital": "North York General Hospital", "Issue": "Recruitment for two Board Governors", "Paragraph blurb": "", "Date": "February 24, 2026", "Source": "North York General Hospital", "Source link": "", "_meta": {"file": "Run 1.docx", "run": "Run 1"}}
    ]
}

for model, data in models_data.items():
    out_path = os.path.join('Parsed_Responses', f"{model}_llm.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
