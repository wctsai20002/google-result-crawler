import os
import time
import html
import gzip
import requests
import subprocess
import urllib.parse
from dotenv import load_dotenv, find_dotenv
from django.core.validators import URLValidator
from django.utils.text import get_valid_filename
from bs4 import BeautifulSoup as bs
from lxml import etree
from glob import glob

# load .env variable
def load_env_var():
    try:
        load_dotenv(find_dotenv())
        base_url = os.getenv("BASE_URL")
        maximum_page = int(os.getenv("MAXIMUM_PAGE"))
        use_keyword = str_to_bool(os.getenv("USE_KEYWORD"))
        use_url = str_to_bool(os.getenv("USE_URL"))
        user_agent = os.getenv("USER_AGENT")
        download_log = str_to_bool(os.getenv("DOWNLOAD_LOG"))
    except Exception as e:
        print("Make sure you have .env file and in correct format !!!")
        raise
    
    return {
        "BASE_URL" : base_url, 
        "MAXIMUM_PAGE" : maximum_page, 
        "USE_KEYWORD" : use_keyword, 
        "USE_URL" : use_url, 
        "USER_AGENT" : user_agent, 
        "DOWNLOAD_LOG" : download_log
        }

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
def download_keyword_data(base_url, keywords, maximum_page, user_agent, download_log):
    for keyword in keywords:
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
            wget_download("keywords", search_url, index_page_path, user_agent, download_log)
            new_index_page_path = rename_html_file(index_page_path, "index_page.html")

            # wget result
            download_and_replace_result(page_path, new_index_page_path, user_agent, download_log)

        replace_page_number_href(keyword_path, maximum_page)

def download_and_replace_result(page_path, index_page_path, user_agent, download_log):
    html_code = ""
    with open(index_page_path, "r+", encoding="utf-8") as f:
        html_code = f.read()
    
        # get results by xpath
        selector = etree.HTML(html_code)
        elements = selector.xpath('//div[@id="rso"]/div[@class="g"]/div[@class="rc"]/div[@class="r"]/a')
        hrefs = [ele.xpath("@href")[0] for ele in elements]

        # make result dir
        for i, href in enumerate(hrefs):
            vaild_filename = valid_filename_by_url(href)
            result_path = page_path.rstrip("/") + "/" + vaild_filename
            if not os.path.isdir(result_path):
                os.mkdir(result_path)
            else:
                print("Duplicate result of : ", href)
                continue

            # wget result
            wget_download("keywords", href, result_path, user_agent, download_log)
            new_result_path = rename_html_file(result_path, "result_" + str(i + 1) + ".html")

            # replace result href
            if new_result_path:
                old_result_href = html.escape(href)
                start = new_result_path.find(vaild_filename) + len(vaild_filename)
                new_result_href = "../" + vaild_filename + new_result_path[start:]
                html_code = html_code.replace(old_result_href, new_result_href)
        
        # overwrite
        f.seek(0)
        f.write(html_code)
        f.truncate()

def download_url_data(urls, user_agent, download_log):
    for url in urls:
        vaild_filename = valid_filename_by_url(url)
        url_path = "./download_data/urls/" + vaild_filename
        if not os.path.isdir(url_path):
            os.mkdir(url_path)
        else:
            print("Duplicate url of : ", url)
            continue
        wget_download("urls", url, url_path, user_agent, download_log)
        new_html_path = rename_html_file(url_path, "result.html")

def rename_html_file(path, file_name):
    html_name = ""
    raw_html = ""
    for root, dirs, files in os.walk(path):
        for f in files:
            new_root = root.replace("\\", "/") + "/"
            if (f.endswith(".html") or f.endswith(".htm")) and "robots.txt" not in f:
                html_name = new_root + f
                new_name = new_root + file_name
            elif f.endswith(".html.backup"):
                raw_html = new_root + f
                new_name = new_root + file_name
    
    if html_name or raw_html:
        old_name = html_name if html_name else raw_html
        os.rename(old_name, new_name)

        # decompress gzip file and delete
        decompress_gzip(path)
        with open(new_name, "r+", encoding="utf-8", errors="ignore") as f:
            html_code = f.read()
            html_code = html_code.replace(".js.gz", ".js").replace(".css.gz", ".css")
            f.seek(0)
            f.write(html_code)
            f.truncate()
        return new_name
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

def wget_download(species, url, path, user_agent, download_log, download_raw = True):
    # sometimes wget will failed, so backup by requests
    if download_raw:
        download_raw_html(url, path, user_agent)
    
    # store download url
    path = path.rstrip("/") + "/"
    with open(path + "download_url.txt", "w", encoding="utf-8") as f:
        f.write(url)
    
    url = '"' + url + '"'
    path = '"' + path + '"'
    user_agent = ' --user-agent="User-Agent: ' + user_agent + '" '
    local_path = "-P " + path
    wget_command = "wget -q -p -E -k -K -H -nH -e robots=off --convert-links --no-check-certificate --timeout=5 --waitretry=0 --tries=3 --retry-connrefused --restrict-file-names=windows "
    wget_command = wget_command + local_path + user_agent + url
    log_path = "./download_data/" + species + "/download_log"
    try:
        output_bytes = subprocess.check_output(wget_command, stderr=subprocess.STDOUT)
        if download_log:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(output_bytes.decode("utf-8"))
    except Exception as e:
        if download_log:
            with open(log_path, "a", encoding="utf-8") as f:
                error_message = "subprocess.check_output have an error, use os.system instead !!!\n"
                error_message += (str(e) + "\n")
                error_message += ("Download " + url + " by wget command : " + wget_command + "\n")
                f.write(error_message)
        os.system(wget_command)

# use requests to download html
def download_raw_html(url, path, user_agent):
    path = path.rstrip("/") + "/raw.html.backup"
    header = {"user-agent" : user_agent}
    r = requests.get(url, headers=header, verify=False)
    if r.status_code == requests.codes.ok:
        with open(path, "w", encoding="utf-8") as f:
            f.write(r.text)

def valid_filename_by_url(url):
    url = url.replace("https://", "")
    url = url.replace("http://", "")
    return get_valid_filename(url)[:50]

def decompress_gzip(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            new_root = root.replace("\\", "/") + "/"
            if f.endswith(".js.gz") or f.endswith(".css.gz"):
                gzip_content = b""
                orig_filename = new_root + f
                with gzip.open(orig_filename, "rb") as gzip_file:
                    gzip_content = gzip_file.read()
                os.remove(orig_filename)
                unzip_filename = orig_filename.rstrip(".gz")
                with open(unzip_filename, "wb") as unzip_file:
                    unzip_file.write(gzip_content)

def create_portal_index():
    # get keywords data
    keywords_keyword_path = []
    keywords_path = "./download_data/keywords/"
    page_1_partial_path = "/page_1/index_page/"
    index_page_name = "index_page.html"

    for root, dirs, files in os.walk(keywords_path):
        new_root = root.replace("\\", "/") + "/"
        for f in files:
            if page_1_partial_path in new_root and f == index_page_name:
                keyword = new_root.replace(keywords_path, "")
                keyword = keyword.replace(page_1_partial_path, "")
                page_1_path = new_root + index_page_name
                maxpage = len(glob((keywords_path + keyword).rstrip("/") + "/*/"))
                keywords_keyword_path.append([keyword, page_1_path, maxpage])
    

    # get urls data
    urls_url_path = []
    urls_path = "./download_data/urls/"
    sub_url_dir = glob(urls_path + "*/")
    sub_url_dir = [ele.replace("\\", "/") for ele in sub_url_dir]
    html_name = "result.html"

    for sub_dir in sub_url_dir:
        url = ""
        html_path = ""
        for root, dirs, files in os.walk(sub_dir):
            new_root = root.replace("\\", "/") + "/"
            for f in files:
                if f == "download_url.txt":
                    with open(new_root + f, "r", encoding="utf-8") as f:
                        url = f.read()
                elif f == html_name:
                    html_path = new_root + f
        urls_url_path.append([url, html_path])
    
    # write index.html
    portal_template_path = "./portal/index_template.html"
    portal_index_path = "./portal/index.html"
    keyword_start = "<!-- keyword columns start -->"
    keyword_end = "<!-- keyword columns end -->"
    url_start = "<!-- url columns start -->"
    url_end = "<!-- url columns end -->"
    local_time = time.localtime(time.time())
    date = "-".join([str(local_time.tm_year), str(local_time.tm_mon).zfill(2), str(local_time.tm_mday).zfill(2)])

    with open(portal_template_path, "r", encoding="utf-8") as f:
        template_html = f.read()
        k_s = template_html.find(keyword_start)
        k_e = template_html.find(keyword_end)
        keyword_column_template = template_html[k_s + len(keyword_start) : k_e].replace("<!--", "").replace("-->", "")

        # keyword columns
        keyword_columns = ""
        for ele in keywords_keyword_path:
            keyword = ele[0]
            path = "../" + ele[1].lstrip("./")
            maxpage = ele[2]
            tempt = keyword_column_template.replace("keyword_keyword", keyword)
            tempt = tempt.replace("keyword_maxpage", str(maxpage))
            tempt = tempt.replace("keyword_date", date)
            tempt = tempt.replace("keyword_href", path)
            keyword_columns += tempt

        u_s = template_html.find(url_start)
        u_e = template_html.find(url_end)
        url_columns_template = template_html[u_s + len(url_start) : u_e].replace("<!--", "").replace("-->", "")

        # url columns
        url_columns = ""
        for ele in urls_url_path:
            url = ele[0]
            path = "../" + ele[1].lstrip("./")
            tempt = url_columns_template.replace("url_url", url)
            tempt = tempt.replace("url_date", date)
            tempt = tempt.replace("url_href", path)
            url_columns += tempt
        
        template_html = template_html.replace(keyword_end, keyword_end + keyword_columns)
        template_html = template_html.replace(url_end, url_end + url_columns)
        with open(portal_index_path, "w", encoding="utf-8") as f:
            f.write(template_html)
        
def Crawler():
    env_map = load_env_var()
    keywords, urls = load_txt_data(env_map["USE_KEYWORD"], env_map["USE_URL"])
    download_keyword_data(env_map["BASE_URL"], keywords, env_map["MAXIMUM_PAGE"], env_map["USER_AGENT"], env_map["DOWNLOAD_LOG"])
    download_url_data(urls, env_map["USER_AGENT"], env_map["DOWNLOAD_LOG"])
    create_portal_index()

if __name__ == "__main__":
    Crawler()
