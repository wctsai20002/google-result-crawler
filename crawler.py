import os
import urllib.parse
from dotenv import load_dotenv, find_dotenv
from django.core.validators import URLValidator

# load .env variable
def load_env_var():
    try:
        load_dotenv(find_dotenv())
        base_url = str(os.getenv("BASE_URL"))
        maximum_page = int(os.getenv("MAXIMUM_PAGE"))
        use_keyword = bool(os.getenv("USE_KEYWORD"))
        use_url = bool(os.getenv("USE_URL"))
    except Exception as e:
        print("Make sure you have .env file and be correct format !!!")
        print(e)
    
    return {"BASE_URL" : base_url, "MAXIMUM_PAGE" : maximum_page, "USE_KEYWORD" : use_keyword, "USE_URL" : use_url}

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
    
    return keywords, urls

# wget keyword google search page
# keywords: list
# maximum_page: int
def keyword_search_page(base_url, keywords, maximum_page):
    for keyword in keywords:
        # make dir
        keyword_path = "./download_data/keywords/" + keyword
        if not os.path.isdir(keyword_path):
            os.mkdir(keyword_path)
        else:
            print("Duplicate keyword folder : ", keyword)
            print("Delete the folder if you want to update data !!!")
            print()
            continue

        for page in range(maximum_page):
            # make dir
            page_path = keyword_path + "/page_" + str(page)
            os.mkdir(page_path)
            page_index_path = page_path + "/page_index"
            os.mkdir(page_index_path)

            parameters = {"q" : keyword, "start" : 10 * page}
            search_parameter = urllib.parse.urlencode(parameters)
            search_url = base_url + search_parameter
            print(search_url)

def check_and_make_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)
        return True
    return False

def wget_download(url, path):
    url = '"' + url + '"'
    user_agent = ' --user-agent="User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36" '
    local_path = "-P " + path
    wget_command = "wget -p -E -k -K -H -nH -q "
    wget_command = wget_command + local_path + user_agent + url
    os.system(wget_command)

def crawler():
    env_map = load_env_var()
    keywords, urls = load_txt_data(env_map["USE_KEYWORD"], env_map["USE_URL"])
    keyword_search_page(env_map["BASE_URL"], keywords, env_map["MAXIMUM_PAGE"])
    

if __name__ == "__main__":
    crawler()