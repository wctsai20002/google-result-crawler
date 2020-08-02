import os
import html
import requests
import subprocess
import urllib.parse
from dotenv import load_dotenv, find_dotenv
from django.core.validators import URLValidator
from django.utils.text import get_valid_filename
from bs4 import BeautifulSoup as bs
from lxml import etree

# load .env variable
def load_env_var():
    try:
        load_dotenv(find_dotenv())
        base_url = os.getenv("BASE_URL")
        maximum_page = int(os.getenv("MAXIMUM_PAGE"))
        use_keyword = str_to_bool(os.getenv("USE_KEYWORD"))
        use_url = str_to_bool(os.getenv("USE_URL"))
        user_agent = os.getenv("USER_AGENT")
    except Exception as e:
        print("Make sure you have .env file and in correct format !!!")
        raise
    
    return {"BASE_URL" : base_url, "MAXIMUM_PAGE" : maximum_page, "USE_KEYWORD" : use_keyword, "USE_URL" : use_url, "USER_AGENT" : user_agent}

def str_to_bool(word):
    return True if word.lower() == "true" else False

# load keywords.txt and urls.txt
def load_txt_data(use_keyword, use_url):
    keywords = []
    urls = []
    if use_keyword:
        with open("./keywords.txt", "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f.readlines()]
    if use_url:
        with open("./urls.txt", "r", encoding="utf-8") as f:
            url_validate = URLValidator()
            for line in f.readlines():
                line = line.strip()
                try:
                    url_validate(line)
                    urls.append(line)
                except Exception as e:
                    print("Be sure your url in urls.txt is correct !!!")
                    print("Error url : ", line)
                    raise
    
    return keywords, urls

# wget keyword google search page
# keywords: list
# maximum_page: int
def download_keyword_data(base_url, keywords, maximum_page, user_agent):
    for keyword in keywords:
        print("keyword : ", keyword)
        # make keyword dir
        keyword_path = "./download_data/keywords/" + keyword
        if not os.path.isdir(keyword_path):
            os.mkdir(keyword_path)
        else:
            print("Duplicate keyword folder : ", keyword)
            print("Delete the folder if you want to update data !!!")
            print()
            continue
        
        for page in range(maximum_page):
            # make page dir
            page_path = keyword_path + "/page_" + str(page + 1)
            os.mkdir(page_path)
            index_page_path = page_path + "/index_page"
            os.mkdir(index_page_path)

            parameters = {"q" : keyword, "start" : 10 * page}
            search_parameter = urllib.parse.urlencode(parameters)
            search_url = base_url + search_parameter

            # wget google index page
            wget_download("keywords", search_url, index_page_path, user_agent, False)
            new_index_page_path = rename_html_file(index_page_path, "index_page.html")

            # wget result
            download_and_replace_result(page_path, new_index_page_path, user_agent)

        replace_page_number_href(keyword_path, maximum_page)

def download_and_replace_result(page_path, index_page_path, user_agent):
    html_code = ""
    with open(index_page_path, "r+", encoding="utf-8") as f:
        html_code = f.read()
    
        # get results by xpath
        selector = etree.HTML(html_code)
        elements = selector.xpath('//div[@id="rso"]/div[@class="g"]/div[@class="rc"]/div[@class="r"]/a')
        hrefs = [ele.xpath("@href")[0] for ele in elements]
        titles = [ele.xpath("h3/text()")[0] for ele in elements]

        # make result dir
        for i, href in enumerate(hrefs):
            vaild_filename = get_valid_filename(href)[:30]
            result_path = page_path.rstrip("/") + "/" + vaild_filename
            if not os.path.isdir(result_path):
                os.mkdir(result_path)
            else:
                print("Duplicate result of : ", href)
                continue

            # wget result
            wget_download("keywords", href, result_path, user_agent)
            new_result_path = rename_html_file(result_path, "result_" + str(i + 1) + ".html")
            print("new_result_path : ", new_result_path)

            # replace result href
            if new_result_path:
                old_result_href = html.escape(href)
                start = new_result_path.find(vaild_filename) + len(vaild_filename)
                new_result_href = "../" + vaild_filename + new_result_path[start:]
                html_code = html_code.replace(old_result_href, new_result_href)
                print("replace old : ", old_result_href)
                print("replace new : ", new_result_href)
                print()
        
        # overwrite
        f.seek(0)
        f.write(html_code)
        f.truncate()

def download_url_data(urls, user_agent):
    for url in urls:
        vaild_filename = get_valid_filename(url)[:30]
        url_path = "./download_data/urls/" + vaild_filename
        if not os.path.isdir(url_path):
            os.mkdir(url_path)
        else:
            print("Duplicate url of : ", url)
            continue
        wget_download("urls", url, url_path, user_agent)

def rename_html_file(path, file_name):
    # find .orig to know name of html
    html_name = ""
    for root, dirs, files in os.walk(path):
        for f in files:
            new_root = root.replace("\\", "/") + "/"
            if f.endswith(".html"):
                html_name = new_root + f
                new_name = new_root + file_name
            elif f.endswith(".html.backup"):
                raw_html = new_root + f
                new_name = new_root + file_name
    
    if html_name:
        os.rename(html_name, new_name)
        return new_name
    elif raw_html:
        os.rename(raw_html, new_name)
    else:
        return None

# path need to be specific keyword path like ./download_data/keywords/example keyword
def replace_page_number_href(path, maximum_page):
    path = path.rstrip("/")
    path_prefix = "../../"
    path_suffix = "/index_page/index_page.html"

    for page in range(maximum_page):
        html_path = path + "/page_" + str(page + 1) + path_suffix
        with open(html_path, "r+", encoding="utf-8") as f:
            html_code = f.read()
            soup = bs(html_code, "lxml")
            
            # find and replace page number href
            for i in range(10):
                label_name = "Page " + str(i + 1)
                page_number_element = soup.find("a", {"aria-label" : label_name})
                if page_number_element:
                    old_page_href = html.escape(page_number_element["href"])
                    new_page_href = path_prefix + "page_" + str(i + 1) + path_suffix if i + 1 <= maximum_page else "#"
                    html_code = html_code.replace(old_page_href, new_page_href)
            
            # find and replace next page href
            next_page_element = soup.find("a", {"id" : "pnnext"})
            if next_page_element:
                old_next_href = html.escape(next_page_element["href"])
                new_next_href = path_prefix + "page_" + str(page + 2) + path_suffix if page + 2 <= maximum_page else "#"
                html_code = html_code.replace(old_next_href, new_next_href)
            
            # find and replace prev page href
            prev_page_element = soup.find("a", {"id" : "pnprev"})
            if prev_page_element:
                old_prev_href = html.escape(prev_page_element["href"])
                new_prev_href = path_prefix + "page_" + str(page) + path_suffix if page > 0 else "#"
                html_code = html_code.replace(old_prev_href, new_prev_href)

            # overwrite
            f.seek(0)
            f.write(html_code)
            f.truncate()

def wget_download(species, url, path, user_agent, download_raw = True):
    # sometimes wget will failed, so backup by requests
    if download_raw:
        download_raw_html(url, path, user_agent)
    url = '"' + url + '"'
    path = '"' + path + '"'
    user_agent = ' --user-agent="User-Agent: ' + user_agent + '" '
    local_path = "-P " + path
    wget_command = "wget -p -E -k -K -H -nH --no-check-certificate "
    wget_command = wget_command + local_path + user_agent + url
    os.system(wget_command)
    # output_bytes = subprocess.check_output(wget_command, stderr=subprocess.STDOUT)
    # log_path = "./download_data/" + species + "/download_log"
    # with open(log_path, "a", encoding="utf-8") as f:
    #     f.write(output_bytes.decode("utf-8"))

# use requests to download html
def download_raw_html(url, path, user_agent):
    path = path.rstrip("/") + "/raw.html.backup"
    header = {"user-agent" : user_agent}
    r = requests.get(url, headers=header, verify=False)
    if r.status_code == requests.codes.ok:
        with open(path, "w", encoding="utf-8") as f:
            f.write(r.text)

def Crawler():
    env_map = load_env_var()
    print(env_map)
    keywords, urls = load_txt_data(env_map["USE_KEYWORD"], env_map["USE_URL"])
    download_keyword_data(env_map["BASE_URL"], keywords, env_map["MAXIMUM_PAGE"], env_map["USER_AGENT"])
    download_url_data(urls, env_map["USER_AGENT"])
    

if __name__ == "__main__":
    Crawler()