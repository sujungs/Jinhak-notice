import streamlit as st
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components
from bs4 import BeautifulSoup as bs
import requests
import time
import json
import pandas as pd
import re
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# import pyautogui
# import pyperclip
# from PIL import ImageGrab
import time
import random


headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"}


# style 속성 편집
TABLE_STYLE = "table-layout: auto; border-collapse: collapse; border: 1px solid #000; font-family: sans-serif; font-size:15px; width:100%;"
THEAD_STYLE = ""
TH_STYLE = "border: 1px solid #000; padding: 10px; line-height: 1.6; text-align: center; font-weight: bold;"
TD_CENTER_STYLE = "border: 1px solid #000; padding: 10px; line-height: 1.6; text-align: center;"
TD_LEFT_STYLE = "border: 1px solid #000; padding: 10px; line-height: 1.6; text-align: left;"

# table 형식 변환
def normalize_table(table, soup):

    # 1️ 필요없는 태그 제거
    for decompose_tag in table.find_all(["colgroup", "caption","figure"]):
        decompose_tag.decompose()

    # 2️ table 스타일 강제
    table.attrs = {"style": TABLE_STYLE}

    # 3 thead 스타일
    thead = table.find("thead")
    first_tr = table.find("tr")
    
    if thead:
        thead["style"] = THEAD_STYLE
        for tr in thead.find_all("tr"):
            tr["style"] = "background-color: #f2f2f2; font-weight: bold; text-align: center; border-bottom: 3px double #000;"
            
    elif len(table.find_all("tr")) == 1:
        first_tr["style"] = "font-weight: bold; text-align: center; border-bottom: 1px #000;"
        
    elif first_tr and not first_tr.find("td", rowspan=True):
        first_tr["style"] = "background-color: #f2f2f2; font-weight: bold; text-align: center; border-bottom: 3px double #000;"

    # 4 th 스타일s
    for th in table.find_all("th"):
        th["style"] = TH_STYLE

    # 5 td 스타일 처리
    for td in table.find_all("td"):

        # span 제거 (내용 유지)
        for span in td.find_all(["span", "font"]):
            span.unwrap()
            
        # p 제거(줄바꿈 유지)
        for p in td.find_all("p"):
            p.insert_after(soup.new_tag("br"))
            p.unwrap()

        # 필요한 속성만 유지
        attrs_to_keep = {}
        for k in ["colspan", "rowspan", "valign", "align"]:
            if k in td.attrs:
                attrs_to_keep[k] = td.attrs[k]

        td.attrs = attrs_to_keep    

        # td 스타일 적용
        if len(td.get_text(strip=True)) > 20:
            td["style"] = TD_LEFT_STYLE
        else :
            td["style"] = TD_CENTER_STYLE
    


# HTML 전체 pre 태그로 변환
PRE_STYLE ="word-break: break-word; white-space: pre-wrap; font-family:sans-serif; font-size:15px"
Text_tags = ["p","span","li","strong", "h", "b", "h4", 'h3', "ol", "u"]
Unwarp_tags = ["div", "figure", "ul"]

def contents_pre_tag(soup):
    buffer = []
    remove_nodes = []
    
    for node in soup.find_all(recursive=False):
        
        # table이면 text block → pre태그로 변환
        if getattr(node, "name", None) == "table":

            # 쌓여있는 텍스트가 있을 경우
            if buffer:
                text = "\n".join(buffer)
                text = re.sub(r"\n{3,}", "\n\n", text)

                pre = soup.new_tag("pre")
                pre["style"] = PRE_STYLE
                pre.string = text

                node.insert_before(pre)
                buffer = []

            continue

        # br → 줄바꿈 처리
        if hasattr(node, "find_all"): 
            for br in node.find_all("br"):
                br.replace_with("\n")

        if getattr(node, "name", None) in Unwarp_tags:
            node.unwrap()
        
        
        # 텍스트 태그 buffer에 쌓기
        if getattr(node, "name", None) in Text_tags:
            text = node.get_text(strip=False)
            
            if text:
                buffer.append(text.replace("\xa0"," "))
            
            remove_nodes.append(node)

    # 마지막 text block 처리
    if buffer:
        text = "\n".join(buffer)
        text = re.sub(r"\n{3,}", "\n\n", text)

        pre = soup.new_tag("pre")
        pre["style"] = PRE_STYLE
        pre.string = text

        soup.append(pre)

    # 기존 태그 제거
    for node in remove_nodes:
        node.extract()

def clear_text():   #streamlit session 초기화
        st.session_state.html_input = ""
        st.session_state.output_html = ""

#---------------------------------

# EURAXESS 공고
P_STYLE = "line-height: 1.6; margin-bottom: 15px;"
UL_STYLE = "padding-left: 20px; list-style: none;"
LI_STYLE = "margin-bottom: 10px; line-height: 1.6; font-size: 15px;"

def normalize_eur(html):

    for p in html.find_all("p"):
            p["style"] = P_STYLE

    for ul in html.find_all("ul"):
        ul["style"] = UL_STYLE
        
        for li in ul.find_all("li"):
            li["style"] = LI_STYLE
            text = li.text
            li.string = "• " + text
    
    for ol in html.find_all("ol"):
        ol["style"] = UL_STYLE
        
        for num, li in enumerate(ol.find_all("li")):
            li["style"] = LI_STYLE
            text = li.text
            li.string = str(num+1) + ". " + text
            
    return html



#---------------------------------

# 캐치 공고
def catch_notice(url):
    # url 형식 예: "https://www.catch.co.kr/NCS/RecruitInfoDetails/539080"
    
    req = requests.get(url, headers=headers)
    html = bs(req.text, "html.parser")
    
    # 기업명
    name = html.select_one("h2.name").text
    
    # 공고명
    title = html.select_one("h1.subj").text
    
    # MOA 붙여넣기 내용
    content = f"""<p style="text-align: center; line-height: 2;">
<span style="font-size: 30px;"><strong>[{name}]</strong></span><br>
<strong><span style="font-size: 30px;">{title}</span></strong>
</p><br>
<p style="text-align: center; line-height: 2;">
<span style="font-size: 18px;">상위권 채용 플랫폼, CATCH에서 자세한 공고 내용을 확인해보세요!</span>
</p><br>
<p style="text-align: center;">
<a href="{url}" target="_blank" rel="noopener">
<img src="https://www.jinhakpro.com/api/common/assets/organ/200433/add_0805161233_hq6zg.png" style="width: 280px;">
</a>
</p><br>
"""
    
    return content


# ----------------------------------------------
# 하이브레인넷 공고

# 공고 수집할 페이지
hbn_url = ["https://www.hibrain.net/recruitment/categories/JOB/categories/PROF/recruits?page=1&pagingno=1&listType=ING&pagesize=10&sortType=SORTDTM&cntType=JOB&limit=25&displayType=TIT&siteid=1",
                    "https://www.hibrain.net/recruitment/categories/JOB/categories/PROF/recruits?page=2&pagingno=1&listType=ING&pagesize=10&sortType=SORTDTM&cntType=JOB&limit=25&displayType=TIT&siteid=1",
                    "https://www.hibrain.net/recruitment/categories/JOB/categories/TPROF/recruits?page=1&pagingno=1&listType=ING&pagesize=10&sortType=SORTDTM&cntType=JOB&limit=25&displayType=TIT&siteid=1",
                    "https://www.hibrain.net/recruitment/categories/JOB/categories/TPROF/recruits?page=2&pagingno=1&listType=ING&pagesize=10&sortType=SORTDTM&cntType=JOB&limit=25&displayType=TIT&siteid=1",
                    "https://www.hibrain.net/recruitment/categories/JOB/categories/RES/recruits?page=1&pagingno=1&listType=ING&pagesize=10&sortType=SORTDTM&cntType=JOB&limit=25&displayType=TIT&siteid=1",
                    "https://www.hibrain.net/recruitment/categories/JOB/categories/RES/recruits?page=2&pagingno=1&listType=ING&pagesize=10&sortType=SORTDTM&cntType=JOB&limit=25&displayType=TIT&siteid=1"]

# 공고명 전처리
def normalize(text):
    text = re.sub(r"[^\w\s]", " ", text)  # 괄호 제거
    text = text.upper()
    stopwords = ["공고", "초빙", "모집", "채용", "계획", "공개"]
    tokens = text.split()
    tokens = [t for t in tokens if t not in stopwords]
    return " ".join(tokens)


# 크롤링한 하이브레인넷 공고와 moa 비교
def compare_hbn_moa(row, moa_df):
    
    com_df = moa_df[(moa_df["기관명"] == row[1]) & (moa_df["공고시작일"] == row[3]) & (moa_df["공고종료일"] == row[4])]     # 모아공고 날짜와 하이브레인넷 날짜 확인
    
    vectorizer = TfidfVectorizer()
    vectorizer.fit(moa_df["공고제목"])
    
    for com in com_df.values:
        
        similar = cosine_similarity(vectorizer.transform([normalize(row[2])]), vectorizer.transform([normalize(com[1])]))
        
        if similar >= 0.6:
            return "유사일치"
        else:
            return "애매일치"
    
    return "불일치"


# 크롤링 ing~
def crawl_hibrain(hbn_url, headers, progress_bar = None):
    hbn_data = []

    # 하이브레인넷 url 입력
    for page_idx, url in enumerate(hbn_url):
        response = requests.get(url, headers=headers)
        hbn_html = bs(response.text, 'html.parser')

        # 각 페이지 크롤링
        for li in hbn_html.find_all("li", attrs={"class" : "row sortRoot"}):
            
            idx = li.find("span", class_="td_number number").text.strip()                                               # 순번
            inst_title = li.find("span", class_= "titleImageNone").text.strip().replace("\xa0", " ").split(" ", 1)      # 공고제목 부분 띄어쓰기 기준으로 분리
            institution = inst_title[0]                                                                                 # 기관명
            title = inst_title[1]                                                                                       # 제목
            detail_url = "https://www.hibrain.net/recruitment/recruits/" + li.find("span", class_="td_title").a["href"].split("recruits/")[1].split("?")[0] # url
            
            info_block = li.find("span", class_ = {"infoBlock"})
            
            date_info = info_block.find("span", class_ = "td_receipt").text
            
            try:
                start_date = date_info.split()[0].strip()
                end_date = date_info.split()[2].strip()
                notice_date = info_block.find("span", class_ = "td_rdtm number").text
            
            except:   # 접수기간 칸이 '상시', '채용시까지' 등 문자일 경우
                start_date = date_info.split()[0].strip()
                end_date = None
                notice_date = info_block.find("span", class_ = "td_rdtm number").text

            hbn_data.append([idx, institution, title, start_date, end_date, notice_date, detail_url])
        
        time.sleep(2)
        
        # 진행률 표시
        progress_bar.progress((page_idx+1) / (len(hbn_url)))
    
    return hbn_data

# 전처리 + 비교 후 테이블 반환
def prepro_hbn_df(hbn_df):
    hbn_df = hbn_df.drop_duplicates(subset=["url"]).reset_index(drop=True)      # 중복 공고 제거
        
    hbn_df["접수마감"] = hbn_df["접수마감"].apply(lambda x : (datetime.today() + timedelta(days=1)).strftime("%y.%m.%d") if x == "내일마감" else x)
    
    compare_data = [compare_hbn_moa(row, moa_df) for row in hbn_df.values]
    hbn_df["일치여부"] =  compare_data
    
    if "확인완료" not in hbn_df.columns:
        hbn_df["확인완료"] = False

    hbn_df = hbn_df[["확인완료", "기관명", "제목", "접수시작", "접수마감", "등록/수정일", "url", "일치여부"]]
    
    return hbn_df


#-------------------------------------------------------------
# 페이스북 시딩 자동화

def get_week_of_month(date):
    first_day = date.replace(day=1)
    day_of_week = (first_day.weekday() + 1) % 7
    return (date.day + day_of_week - 1) // 7 + 1


def human_move(x, y, duration=0.01):
    #곡선 형태로 마우스 이동
    start_x, start_y = pyautogui.position()
    
    steps = random.randint(10, 15)
    for i in range(steps):
        t = i / steps

        ease = t * t * (3 - 2 * t)
        
        new_x = start_x + (x - start_x) * ease + random.uniform(-3, 3)
        new_y = start_y + (y - start_y) * ease + random.uniform(-3, 3)
        
        pyautogui.moveTo(new_x, new_y)


def hover_and_click(x, y):
    offset_x = random.randint(-5, 5)
    offset_y = random.randint(-5, 5)
    human_move(x + offset_x, y + offset_y)
    
    final_x = x + random.randint(-5, 5)
    final_y = y + random.randint(-2, 2)
    
    pyautogui.moveTo(final_x, final_y)
    time.sleep(random.uniform(0.2, 0.5))
    pyautogui.click()

def random_mouse_idle():
    for _ in range(random.randint(2, 4)):
        x, y = pyautogui.position()
        pyautogui.moveRel(random.randint(-30, 50), random.randint(-30, 50), duration=random.uniform(0.3, 0.6))

def human_scroll():
    for _ in range(random.randint(2, 3)):       # 몇 번 스크롤 움직일지 설정
        pyautogui.scroll(random.randint(500, 900))
        time.sleep(random.uniform(1, 2))
        pyautogui.scroll(random.randint(-800, 500))
        time.sleep(random.uniform(1, 2))    

def check_image(button_case, confidence=0.8):
    im = ImageGrab.grab(all_screens=True) #bbox=(2000, 300, 3600, 900)
    im.save('dual_monitor_screenshot.png')
    if button_case == "글쓰기":
        location = pyautogui.locate(r"C:\Users\psj\Desktop\project\facebook\write_box.png", 'dual_monitor_screenshot.png', confidence=confidence)
           
    elif button_case == "게시":
        location = pyautogui.locate(r"C:\Users\psj\Desktop\project\facebook\post_button.png", 'dual_monitor_screenshot.png', confidence=confidence)

    return pyautogui.center(location)


url_list = {"통계학" : "majorCodes%5B%5D=20402",
            "컴퓨터공학" : "majorCodes=30204&majorCodes=30207",
            "마케팅" : "majorCodes=10609&majorCodes=10606", 
            "기계공학" : "majorCodes=30506&majorCodes=30509&majorCodes=30505",
            "물리과학" : "majorCodes%5B%5D=20406",
            "심리학" : "majorCodes%5B%5D=10306", 
            "바이오" : "majorCodes=20105&majorCodes=20103&majorCodes=30104",
            "공학" : "majorCodes%5B%5D=30101&majorCodes%5B%5D=30102&majorCodes%5B%5D=30103&majorCodes%5B%5D=30104&majorCodes%5B%5D=30105&majorCodes%5B%5D=301&majorCodes%5B%5D=30201&majorCodes%5B%5D=30202&majorCodes%5B%5D=30203&majorCodes%5B%5D=30204&majorCodes%5B%5D=30205&majorCodes%5B%5D=30206&majorCodes%5B%5D=30207&majorCodes%5B%5D=30208&majorCodes%5B%5D=302&majorCodes%5B%5D=30301&majorCodes%5B%5D=30302&majorCodes%5B%5D=30303&majorCodes%5B%5D=30304&majorCodes%5B%5D=30305&majorCodes%5B%5D=303&majorCodes%5B%5D=30401&majorCodes%5B%5D=30402&majorCodes%5B%5D=30403&majorCodes%5B%5D=304&majorCodes%5B%5D=30501&majorCodes%5B%5D=30502&majorCodes%5B%5D=30503&majorCodes%5B%5D=30504&majorCodes%5B%5D=30505&majorCodes%5B%5D=30506&majorCodes%5B%5D=30508&majorCodes%5B%5D=30509&majorCodes%5B%5D=305&majorCodes%5B%5D=30601&majorCodes%5B%5D=30602&majorCodes%5B%5D=306&majorCodes%5B%5D=30701&majorCodes%5B%5D=30702&majorCodes%5B%5D=30703&majorCodes%5B%5D=30704&majorCodes%5B%5D=30705&majorCodes%5B%5D=30706&majorCodes%5B%5D=307&majorCodes%5B%5D=3",
            "인문학" : "majorCodes%5B%5D=101",
            "수학" :"majorCodes%5B%5D=20405", 
            "경제학" : "majorCodes=10608&majorCodes=10604&majorCodes=10601"
            }

def load_major_content(find_major_list, headers, progress_bar = None):  # major : 리스트
    # 전공별 공고
    base_url = "https://www.jinhakpro.com/api/applicant/recruit/search?searchText&isIncludeEndRecruit=false&isOnlyOnlineApply=false&sortType=3&currentPage=1&itemCount=16&"

    major_content = {}
    idx = 1
    
    for major in find_major_list:
        # html = requests.get(f"{base_url}{url_list[major]}", headers=headers)        # 각 전공별 url → json 형태로 크롤링
        # data = html.json()
        
        with open(f"data/{major}.json", encoding="utf-8") as f:
            data = json.load(f)

        # recruitIdx, 기관명, 공고명, 채용구분, 공고마감일, 지역
        df = pd.DataFrame(data['list'])[["recruitIdx", "organName", "recruitTitle", "recruitTypeCode", "originApplyEndTime", "regionData"]]
        
        # 해외 포닥은 최대한 뒤로
        df["recruitTypeCode"] = df["recruitTypeCode"].apply(lambda x : "전임교원" if x == "P" else "비전임교원" if x == "T" else "연구원" if x == "RS" else "강사")
        df["originApplyEndTime"] = pd.to_datetime(df["originApplyEndTime"]).dt.strftime('%Y.%m.%d')
        df["regionData"] = df["regionData"].apply(lambda x : x[0]["region"] if x[0]["region"] != "해외" else f"{x[0]['region']}({x[0]['national_name']})")
        df = df.sort_values(["regionData", "originApplyEndTime"], ascending=[True, False]).head(10)
        
        content = f"""※ 진학프로에서 {datetime.today().month}월 {get_week_of_month(datetime.today())}주차 {major} 인기 채용공고를 알려드립니다🔔
"""
        
        for n in df.values:
            content += f"""
[{n[1]}] {n[2]}
· 채용분야: {n[3]}
· 근무지역: {n[5]}
· 마감일자: {n[4]}
· 공고링크: https://www.jinhakpro.com/recruit/{n[0]}?utm_source=facebook&utm_medium=referral&utm_campaign=fbgroup
"""
        major_content[major] = content
        
        time.sleep(2)
        
        # 진행률 표시
        progress_bar.progress(idx / (len(find_major_list)))
        idx += 1
        
    return major_content

#----------------------------------------------------------------------------------------------------------------------------
# 메인 화면 및 사이드 메뉴

# 사이드바 설정
# with st.sidebar:
#     option = option_menu("메뉴", ["TABLE HTML", "EURAXESS", "CATCH 공고", "하이브레인넷", "Facebook 그룹"],
#                          icons=['house','bank', 'kanban', 'bi bi-robot', 'card-heading' ],
#                          menu_icon="menu-button", default_index=0,
#                          styles={
#         "container": {"padding": "5px", "background-color": "#fafafa", "width" : "260px", "margin" : "0"},
#         "icon": {"color": "black", "font-size": "17px"},
#         "nav-link": {"font-size": "14px", "text-align": "left"},
#         "nav-link-selected": {"background-color": "#1FA8E1"},
#     })

with st.sidebar:
    option = option_menu("메뉴", ["TABLE HTML", "EURAXESS", "하이브레인넷", "Facebook 그룹"],
                         icons=['house','bank', 'bi bi-robot', 'card-heading' ],
                         menu_icon="menu-button", default_index=0,
                         styles={
        "container": {"padding": "5px", "background-color": "#fafafa", "width" : "260px", "margin" : "0"},
        "icon": {"color": "black", "font-size": "17px"},
        "nav-link": {"font-size": "14px", "text-align": "left"},
        "nav-link-selected": {"background-color": "#1FA8E1"},
    })


# 사이드바 너비 고정    
st.markdown("""
<style>
section[data-testid="stSidebar"] ul.nav {
    width: 260px !important;
}
section[data-testid="stSidebar"] ul.nav li {
    width: 260px !important;
}
</style>
""", unsafe_allow_html=True)


st.title("공고 등록 🚀")

# A옵션    
if option == "TABLE HTML":
    
    # 화면 너비 조절 CSS
    st.markdown("""
        <style>
        .block-container {
            max-width: 1600px;
            padding-left: 4rem;
            padding-right: 4rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    part1, b, part2 = st.columns([6, 0.5, 3])
    
    with part1:
        if "html_input" not in st.session_state:
            st.session_state.html_input = ""

        if "output_html" not in st.session_state:
            st.session_state.output_html = ""
            
        message = st.text_area("HTML을 입력하세요", height=250, key="html_input")

        st.markdown("""<style>.button-wrap {display:flex; justify-content:flex-end; gap:5px;
        margin-top:-5px;} </style>""", unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([7,1,1,1])
        
        # html 수정 모드 설정
        with col1:
            selected_mode = st.radio("Mode", ["전체 수정", "Table만 수정"])

        # pre 태그 복사
        with col2:
            text_to_copy = "<pre style='word-break: break-word; white-space: pre-wrap; font-family:sans-serif; font-size : 15px'></pre>"

            components.html(f"""
            <button onclick="copyText()"
            style = "font-size:24px;
                cursor:pointer;
                border:0px solid #FFFFFF;
                background-color:white;">
            📋
            </button>
            <script>
            const textToCopy = {json.dumps(text_to_copy)};

            function copyText() {{
                navigator.clipboard.writeText(textToCopy);
            }}
            </script>""", height=40)
        
        # 입력 버튼
        with col3:
            run = st.button("입력")

        # 입력 칸 삭제 버튼
        with col4:
            st.button("삭제", on_click=clear_text)

        if run and st.session_state.html_input:         # 입력 버튼 클릭시
            
            if selected_mode == "Table만 수정":
                soup = bs(st.session_state.html_input, "html.parser")
                for table in soup.find_all("table"):        # 테이블 수정
                    normalize_table(table, soup)

                st.session_state.output_html = str(soup)
                
            elif selected_mode == "전체 수정":
                soup = bs(st.session_state.html_input, "html.parser")
                
                for unwrap_tag in soup.find_all(Unwarp_tags):
                    unwrap_tag.unwrap()
                
                for table in soup.find_all("table"):        #테이블 수정
                    normalize_table(table, soup)
                
                contents_pre_tag(soup)      # 본문 수정

                output = str(soup).replace("<o:p></o:p>", "")       # 필요없는 태그 삭제
                output = re.sub(r"\n{4,}", "\n\n", output)          # 과도한 줄바꿈 2줄로 축소
                
                st.session_state.output_html = output
        
        # 결과 영역
        if st.session_state.output_html:
            st.markdown("<hr style='margin:0px 0px;'>", unsafe_allow_html=True)
            st.markdown("✅ HTML 코드")
            st.code(st.session_state.output_html, language="html", height=250)
            # st.code(st.session_state.output_html, language="html")
    
    with part2:
        st.markdown("✅ 미리보기")
        st.components.v1.html(st.session_state.output_html,height=600,scrolling=True)


# B옵션
if option == "EURAXESS":
    content = ""
    
    url = st.text_area("URL을 입력하세요", height = 50)
    if url:
        eur_html = bs(requests.get(url, headers=headers).text, "html.parser")
        eur_div = eur_html.find_all("div", class_ = "ecl-u-mb-2xl")
        
        # content 초기화
        content = ""
    
    colb_1, colb_2, colb_3, colb_4 = st.columns([1,1,1,0.5])
    with colb_1:
        if st.checkbox('offer_description', value=True):
            try : 
                offer_description = eur_div[1].find("div", class_="ecl")
                normalize_eur(offer_description)
                content += str(offer_description)
            except:
                pass
            
    with colb_2:
        if st.checkbox("requirements"):
            requirements = eur_div[3]
            content += str("<br>")
            
            for rh, req in zip(requirements.find_all("div", class_="ecl-u-type-bold ecl-u-mb-m"), requirements.find_all("div", class_="ecl")):
                content += f'<p style="line-height: 1.6; margin-bottom: 15px;"><strong>{rh.text}</strong></p>'
                normalize_eur(req)
                content += str(req)
            

    with colb_3:
        if st.checkbox("additional_information"):
            
            additional_information = eur_html.find("h2", id="additional-information").find_parent("div")
                
            for add, inf in zip(additional_information.find_all("div", class_="ecl-u-type-bold ecl-u-mb-m"), additional_information.find_all("div", class_="ecl")):
                content += f'<p style="line-height: 1.6; margin-bottom: 15px;"><strong>{add.text}</strong></p>'
                normalize_eur(inf)
                content += str(inf)
        
    st.markdown("---")
    st.markdown("✅ HTML 코드")
    st.code(content, language="html", height=100)     


# C옵션
if option == "CATCH 공고":
    colc_1, colc_2, colc_3 = st.columns([1,1,5])
    
    with colc_1:
        st.link_button("캐치 1️⃣ ", "https://www.catch.co.kr/NCS/RecruitSearch?search=%EC%97%B0%EA%B5%AC&education=5,6,7")
    
    with colc_2:
        st.link_button("캐치 2️⃣", "https://www.catch.co.kr/NCS/RecruitSearch?search=R%26D&education=5,6,7)")
    
    catch_url = st.text_area("URL을 입력하세요", height = 50)
    
    if catch_url:
        catch_content = catch_notice(catch_url)
        st.code(catch_content, language="markdown")


# D옵션
if option == "하이브레인넷":
    
    # 화면 너비 조절 CSS
    st.markdown("""
        <style>
        .block-container {
            max-width: 1600px;
            padding-left: 3rem;
            padding-right: 3rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 오류 방지를 위한 빈 df 선언
    if "hbn_df" not in st.session_state:
        st.session_state.hbn_df = pd.DataFrame([], columns = ["순번","기관명", "제목", "접수시작", "접수마감", "등록/수정일", "url", "일치여부", "확인완료"])

    if "moa_df" not in st.session_state:
        st.session_state.moa_df = None
    
    # '게재중인 공고' 파일 등록 & 비교를 위한 전처리
    uploaded_file = st.file_uploader("MOA 공고파일을 업로드하세요")
    if uploaded_file is not None:
        moa_df = pd.read_excel(uploaded_file)   
        moa_df["공고시작일"] = [i.replace("-", ".")[2:] for i in moa_df["공고시작일"]]
        moa_df["공고종료일"] = [i.replace("-", ".")[2:] for i in moa_df["공고종료일"]]

        st.session_state.moa_df = moa_df
    
    # 미리보기
    if st.session_state.moa_df is not None:
        with st.expander("file"):
            st.dataframe(st.session_state.moa_df)

    # 비교 시작 버튼
    if st.button("공고비교 시작"):
        progress_bar = st.progress(0)

        hbn_data = crawl_hibrain(hbn_url, headers, progress_bar)
        hbn_df = pd.read_excel("hbn_df.xlsx")
        # hbn_df = pd.DataFrame(hbn_data, columns = ["순번", "기관명", "제목", "접수시작", "접수마감", "등록/수정일", "url"])

        st.session_state.hbn_df = prepro_hbn_df(hbn_df)
        
        
    # 결과창
    tab1, tab2, tab3, tab4 = st.tabs(['불일치', '일치', "MOA", "하이브레인넷"])
    
    with tab1:
        
        # 불일치 및 애매일치 공고 필터링
        filtered_df = st.session_state.hbn_df[(st.session_state.hbn_df["일치여부"].isin(["불일치", "애매일치"])) & 
                                            (st.session_state.hbn_df["접수마감"] != "오늘마감") &
                                            (st.session_state.hbn_df["확인완료"] != True)].sort_values(["등록/수정일", "기관명"], ascending=True)
        
        edited_df = st.data_editor(filtered_df,
                                   column_config={"확인완료": st.column_config.CheckboxColumn("업로드 완료"),
                                                  "url": st.column_config.LinkColumn("공고보기")},
                                   hide_index=True, key = "hbn_editor", height=400)
        
        # 체크박스 저장
        if st.button("업로드 완료 저장"):
            st.session_state.hbn_df.update(edited_df)
    
    with tab2:
        st.dataframe(st.session_state.hbn_df[st.session_state.hbn_df["일치여부"] == "유사일치"], hide_index=True,
                    column_config={"url": st.column_config.LinkColumn("공고보기")}, height = 400 )

    with tab3:
        st.dataframe(st.session_state.moa_df, hide_index=True)

    with tab4:
        st.dataframe(st.session_state.hbn_df, hide_index=True)
        
# 사이드바 기관 검색 기능
inst = st.sidebar.text_input("기관 검색")

if inst:
    try:
        moa_view = st.session_state.moa_df[st.session_state.moa_df["기관명"].str.contains(inst, na=False)][["공고제목", "공고시작일", "공고종료일"]].sort_values("공고시작일", ascending=False)
        st.sidebar.dataframe(moa_view, hide_index=True, height=350)
    except:
        st.sidebar.error("모아 파일을 먼저 업로드해주세요", icon="🚨")


# E옵션
if option == "Facebook 그룹":
    st.write("📢 전공별 페이스북 게시글 관리")
    
    if "major_content" not in st.session_state:
        st.session_state.major_content = {}
        
    majors = st.multiselect("발행할 전공을 선택하세요", options = url_list, default = url_list)
    
    if st.button("전공별 게시글 생성"):
        progress_bar = st.progress(0)
        st.session_state.major_content = load_major_content(majors, headers, progress_bar)

    st.divider()
    
    if st.session_state.major_content:
        selected_major = st.selectbox("전공을 선택하세요", majors)
        
        # 수정 및 미리보기 영역
        st.write(f"### ✏️ {selected_major} 게시글 수정")
        
        # text_area의 value를 session_state와 연결
        edited_text = st.text_area(value=st.session_state.major_content[selected_major],
            label="게시글 수정", label_visibility="collapsed",
            height=400, key=f"editor_{selected_major}")     # 각 전공별 고유 키 부여

        # 수정된 내용을 세션에 반영
        st.session_state.major_content[selected_major] = edited_text

        # 확인 후 페이스북 게시 시작
        if st.button("📨페이스북 자동 발행 시작"):
            seeding_list = pd.read_csv('facebook_seeding_list.csv', encoding='cp949')
            seeding_list = seeding_list[seeding_list['전공'].isin(majors)]
            
            st.warning("5초 뒤에 자동화를 시작합니다. 페이스북 창을 열어두세요! (화면크기: 100%)")
            status_auto = st.empty()
            time.sleep(5)
            
#             success_list = []
#             fail_list = []
#             fail_text = ""
            
#             for index, row in seeding_list.iterrows():
#                 pyautogui.click(x=2328, y=61)
#                 pyperclip.copy(row["링크"])
#                 pyautogui.hotkey('ctrl', 'v')
#                 pyautogui.hotkey('enter')
                
#                 try :
#                     # [단계 1] 게시 버튼 클릭 (좌표 기반)
#                     time.sleep(random.uniform(3, 5))
#                     loc = check_image("글쓰기", confidence=0.8)     # 글쓰기 버튼 찾기
                    
#                     hover_and_click(loc.x*0.95, loc.y*0.8)      # 듀얼 모니터 -> 화면 배율이 안 맞아 오류가 나기 때문에 비율 맞춰주기
                
#                     random_mouse_idle()
#                     time.sleep(random.uniform(1, 2))
                    
#                     # 이미 클릭된 입력창에 멘트 작성
#                     content = st.session_state.major_content[row["전공"]]
#                     pyperclip.copy(content)
#                     pyautogui.hotkey('ctrl', 'v')
                    
#                     time.sleep(random.uniform(1, 2))
#                     human_move(2702, 428)               # (글쓰기 창 중앙 x,y 좌표 입력)
#                     human_scroll()
                    
#                     check_image("게시", confidence=0.9)

#                     random_mouse_idle()
                    
#                     # [단계 3] 게시 버튼 클릭 (좌표 기반)
#                     hover_and_click(2666, 766)              # 게시 버튼 좌표 설정 필요
                    
#                     success_list.append(row)
#                     status_auto.success(f"✅ {row['그룹명']} 발행 완료!")

#                 except Exception as e:
#                     fail_list.append(row)
#                     fail_text += f"""{row['그룹명']}({row['전공']}) : {row["링크"]}\n\n"""
#                     status_auto.error(f"❌ {row['그룹명']} 발행 실패: {e}")
                    
#                 #[단계 4] 다음 작업을 위한 충분한 휴식 (봇 탐지 방지)
#                 time.sleep(random.uniform(8, 12))
            
            
#             # 게시 작업 종료 후 결과 Excel 기록   
#             result_report = pd.read_excel("페이스북 시딩 결과.xlsx")
#             result_report.loc[len(result_report)] = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(success_list)]
#             result_report.to_excel("페이스북 시딩 결과.xlsx", index=False)
            
#             # 화면에 표시
#             st.write("### 🏁 작업 완료 리포트")
#             st.success(f"성공: {len(success_list)}건 / 실패: {len(fail_list)}건")
#             st.write(fail_text)
                





