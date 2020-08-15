# google-result-crawler

### Introduction
This is a crawler to download full web page of google result and convert links in html by wget.
Besides search results, it will also download google search page and replace href of results, 
page number and prev/next page button in html to local file path which downloaded by wget.
To look over download data, there is a html [(./portal/index.html)](https://github.com/wctsai20002/google-result-crawler/blob/master/portal/index.html) to access data downloaded by wget.

### Requirements
- [wget for windows](http://gnuwin32.sourceforge.net/packages/wget.htm)

### Getting the code
```
git clone https://github.com/wctsai20002/google-result-crawler.git
```

### Configuration

#### Install modules
```
pip3 install -r ./requirements.txt
```

#### Make .env file
copy or rename .env.example to make .env file, and change variables according to your needs

#### Required data
put keywords and urls you want to download in keywords.txt and urls.txt line by line

### Start
```
python3 ./crawler.py
```
