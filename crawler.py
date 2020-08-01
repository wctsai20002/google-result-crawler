import os
import html
import urllib.parse
from dotenv import load_dotenv, find_dotenv
from django.core.validators import URLValidator
from django.utils.text import get_valid_filename
from bs4 import BeautifulSoup as bs

# load .env variable
def load_env_var():
    try:
        load_dotenv(find_dotenv())
        base_url = os.getenv("BASE_URL")
        maximum_page = int(os.getenv("MAXIMUM_PAGE"))
        use_keyword = str_to_bool(os.getenv("USE_KEYWORD"))
        use_url = str_to_bool(os.getenv("USE_URL"))
    except Exception as e:
        print("Make sure you have .env file and in correct format !!!")
        raise
    
    return {"BASE_URL" : base_url, "MAXIMUM_PAGE" : maximum_page, "USE_KEYWORD" : use_keyword, "USE_URL" : use_url}

def str_to_bool(word):
    return True if word.lower() == "true" else False

# load keywords.txt and urls.txt
def load_txt_data(use_keyword, use_url):
    keywords = []
    urls = []
    if use_keyword:
        with open("./keywords.txt", "r") as f:
            keywords = [line.rstrip("\n") for line in f.readlines()]
    if use_url:
        with open("./urls.txt", "r") as f:
            url_validate = URLValidator()
            for line in f.readlines():
                line = line.rstrip("\n")
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
def keyword_search_page(base_url, keywords, maximum_page):
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
        
        index_page_list = []
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
            wget_download(search_url, index_page_path)
            new_index_page_path = rename_index_page(index_page_path)
            index_page_list.append(new_index_page_path)
        
        replace_page_number_href(keyword_path, maximum_page)

def rename_index_page(path):
    # find .orig to know name of html
    html_name = ""
    for f in os.listdir(path):
        if f.endswith(".orig"):
            html_name = f.rstrip(".orig") + ".html"
    
    path = path.rstrip("/")
    html_name = path + "/" + html_name
    new_name = path + "/index_page.html"
    os.rename(html_name, new_name)
    return new_name

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

def wget_download(url, path):
    url = '"' + url + '"'
    path = '"' + path + '"'
    user_agent = ' --user-agent="User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36" '
    local_path = "-P " + path
    wget_command = "wget -p -E -k -K -H -nH -q "
    wget_command = wget_command + local_path + user_agent + url
    os.system(wget_command)

def crawler():
    env_map = load_env_var()
    print(env_map)
    keywords, urls = load_txt_data(env_map["USE_KEYWORD"], env_map["USE_URL"])
    keyword_search_page(env_map["BASE_URL"], keywords, env_map["MAXIMUM_PAGE"])
    

if __name__ == "__main__":
    crawler()