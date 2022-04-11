import asyncio
import re
import string
import html
from email.mime import text, multipart
import smtplib
import ssl
from io import StringIO

import aiohttp
import flask  # FoxFire99
from apscheduler.schedulers.background import BackgroundScheduler
from markdown import Markdown

# https://www.nltk.org/
# https://stackapps.com/apps/oauth/view/22587

app = flask.Flask(__name__, static_folder='static', static_url_path="")
wolframID = "E5XQJP-AR8P58K4HL"
githubKey = "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"
emailPassword = "FoxFire99"
# Encryption key for the browser session
app.secret_key = "160DA98BE181F8F67DCD9B74FC16AEB2G5C8D667C62DE99139B4A1Z84189DFA5"
app.config["SERVER_NAME"] = "www.foxfire.fyi"
app.config["PREFERRED_URL_SCHEME"] = "https"
# Required by reddit so they can identify my project
userAgent = "webApp:oWRPm7rMWyrKXXFQs83pKg:v1.0.0 (by /u/OliMations)"
scheduler = BackgroundScheduler()
# This gibberish matches almost anything that a dodgy html output will serve and removes it making text readable
htmlCleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')

categoryList = [{"name": "Standard", "id": 1, "apis": {  # Defines all the categorys and their APIs
    "WolframAlpha": {"name": "WolframAlpha",  "critical": False, "logo": "wolfram.jpg", "runner": "wolframAPI", "baseURL": "https://api.wolframalpha.com", "ping": 0, 
                     "status": None, "desc": "WolframAlpha is a computational knowledge engine. It answers factual queries directly by computing the \
                         answer from externally sourced data."},

    "Wikipedia": {"name": "Wikipedia ★", "critical": True, "logo": "wikipedia.png", "runner": "wikimediaAPI", "baseURL": "https://en.wikipedia.org", "ping": 0, "status": True,
                  "desc": "Wikipedia is the world famous free online encyclopedia and holds over 6 million different articles"},

    "Reddit": {"name": "Reddit", "critical": False, "logo": "reddit.png", "runner": "redditAPI", "baseURL": "https://reddit.com", "ping": 0, "status": True,
               "desc": "Reddit is a social news aggregation, web content rating, and discussion website. Registered members submit content to the site such as links, \
                   text posts, images, and videos, which are then voted up or down by other members."}

}}, {"name": "Programming", "id": 2, "apis": {
    "Reddit": {"name": "Reddit", "critical": False, "logo": "reddit.png", "runner": "redditAPI", "baseURL": "https://reddit.com", "ping": 0, "status": True,
               "desc": "Reddit is a social news aggregation, web content rating, and discussion website. Registered members submit content to the site such as links, \
                   text posts, images, and videos, which are then voted up or down by other members."},

    "StackExchange": {"name": "Stack Exchange ★", "critical": True, "logo": "stackexchange.png", "runner": "stackexchangeAPI", "baseURL": "https://api.stackexchange.com", 
                      "ping": 0, "status": True, "desc": "Stack Exchange is a network of question-and-answer websites (including stack overflow) on topics in \
                          diverse fields, each site covering a specific topic."},

    "Github": {"name": "Github ★", "critical": True, "logo": "github.png", "runner": "githubAPI", "baseURL": "https://github.com", "ping": 0, "status": True,
               "desc": "Github is the worlds hub for open source software and code."},

    "ReadtheDocs": {"name": "Read the Docs", "critical": False, "logo": "readthedocs.png", "runner": "readthedocsAPI", "baseURL": "https://readthedocs.org", "ping": 0,
                    "status": True, "desc": "[Needs Github API to work] The worlds biggest open source repository for software documentation"}
}}]
# Used by the search optimiser to just pullout key words
fluffWords = ["to", "and", "but", "are", "do", "my", "i", "on", "or", "would", "when", "the", "by", "as",
              "an", "of", "it", "for", "that", "from", "there", "who", "can", "have"]  
extraDetailedFluff = ["how", "use", "what", "is", "make", "change", "run", "from"]


# Patching the python "markdown" package to allow it to strip all markdown from a response
def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# All still part of the patch, redefining some code in the original module to our custom function above
Markdown.output_formats["plain"] = unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False


async def wolframAPI(data):
    searchValue = data["searchTerm"]
    
    baseURL = "https://api.wolframalpha.com/v2/query" + \
        "?appid=" + wolframID + "&output=json" + "&format=plaintext"
    finalURL = baseURL + "&input=" + "%20".join(searchValue)
    print("Collating:", finalURL)

    finalResult = {"success": True, 
                   "name": "Wolfram:Alpha", 
                   "humanData": []}
    
    jsonResp = await request(finalURL, {})
    if jsonResp[0] != 200:
        for n, _ in enumerate(categoryList):
            try: categoryList[n]["apis"]["WolframAlpha"]["status"] = False
            except KeyError: pass
        return finalResult
    else:
        jsonResp = jsonResp[1]

    url = "https://www.wolframalpha.com/input/?i=" + "%20".join(searchValue)
    if "pod" in jsonResp:
        for pod in jsonResp["queryresult"]["pods"]:
            if "subpods" in pod:
                for subpod in pod["subpods"]:
                    if "plaintext" in subpod and len(subpod["plaintext"]) > 20:
                        finalResult["humanData"].append({"extract": subpod["plaintext"].replace("\n", " "), 
                                                         "url": url, 
                                                         "title": " ".join(searchValue)})

        if "warnings" in jsonResp["queryresult"]:
            if "spellcheck" in jsonResp["queryresult"]:
                finalResult["spellcheck"] = jsonResp["queryresult"]["spellcheck"]

        if jsonResp["queryresult"]["success"] != True:
            finalResult["success"] = False
            if "didyoumeans" in jsonResp["queryresult"]:
                finalResult["didyoumean"] = jsonResp["queryresult"]["didyoumeans"]
            if "tips" in jsonResp["queryresult"]:
                finalResult["tips"] = jsonResp["queryresult"]["tips"]
            if "languagemsg" in jsonResp["queryresult"]:
                finalResult["languagemsg"] = jsonResp["queryresult"]["languagemsg"]
        else:
            finalResult["success"] = True
    else:
        finalResult["success"] = False

    return finalResult


async def redditAPI(data):
    searchValue = data["searchTerm"]
    
    if "redditToken" not in flask.session:
        result = await redditAuth()
        if 200 not in result:
            return {"success": False}

    baseURL = "https://oauth.reddit.com/"
    finalURL = baseURL + "search?type=link&sort=relevance&limit=5" + \
        "&q=" + "%20".join(searchValue)
    print("Collating:", finalURL)

    headers = {
        'User-Agent': userAgent,
        'Authorization': f"bearer {flask.session['redditToken']}"
    }

    finalResult = {"success": False, 
                   "name": "Reddit", 
                   "humanData": []}

    jsonResp = await request(finalURL, headers)
    if jsonResp[0] == 400:
        for n, _ in enumerate(categoryList):
            try: categoryList[n]["apis"]["Reddit"]["status"] = False
            except KeyError: pass
    elif jsonResp[0] == 403:
        del flask.session["redditToken"]
        return await redditAPI(data)
    else:
        jsonResp = jsonResp[1]
    
    for child in jsonResp["data"]["children"]:
        if int(child["data"]["num_comments"]) > 1:
            finalURL2 = baseURL + "r/" + child["data"]['subreddit'] + "/comments/" + \
                child["data"]["name"].split("_", 1)[-1] + "?sort=top&depth=0&limit=5"
                
            jsonResp2 = (await request(finalURL2, headers))[1]
            finalResult["success"] = True
            for commentChild in jsonResp2[1]["data"]["children"]:
                if "body" in commentChild["data"]:
                    try:
                        title = jsonResp2[0]["data"]["children"][0]["data"]["title"]
                    except:
                        title = "Unknown"
                    body = __md.convert(commentChild["data"]["body"])

                    finalResult["humanData"].append({"extract": body, 
                                                        "title": title, 
                                                        "url": f'https://www.reddit.com{commentChild["data"]["permalink"]}',
                                                        "score": commentChild["data"]["score"]})

    return finalResult


async def wikimediaAPI(data):
    searchValue = data["searchTerm"]
    
    baseSearchURL = "https://en.wikipedia.org/w/api.php?action=query&list=prefixsearch&format=json" + \
        "&pssearch=" + "%20".join(searchValue)
    print("Searching:", baseSearchURL)
    finalResult = {"success": False, 
                   "humanData": [], 
                   "name": "Wikipedia"}

    jsonResp = await request(baseSearchURL, {})
    if jsonResp[0] != 200:
        for n, _ in enumerate(categoryList):
            try: categoryList[n]["apis"]["Wikipedia"]["status"] = False
            except KeyError: pass
        return finalResult
    else:
        jsonResp = jsonResp[1]
        
    searchResults = [result["pageid"] for result in jsonResp["query"]
                        ["prefixsearch"] if "(" not in result["title"]]

    for pageid in searchResults:
        baseURl = "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&exsectionformat=wiki&format=json" + \
            "&pageids=" + str(pageid)
        print("Collating:", baseURl)

        jsonResp = await request(baseURl, {})
        if jsonResp[0] != 200:
            return finalResult
        else:
            jsonResp = jsonResp[1]

        for num, result in enumerate(jsonResp["query"]["pages"]):
            if num >= 4:
                break
            title = jsonResp["query"]["pages"][result]["title"]
            accessURL = "https://en.wikipedia.org/wiki/" + \
                title.replace(" ", "_")
            extract = jsonResp["query"]["pages"][result]["extract"]
            extract = re.sub(
                r"==.*?==", " ", extract).replace("\n", "").replace("\\", "")
            finalResult["humanData"].append(
                {"url": accessURL, 
                 "title": title, 
                 "extract": extract})

    finalResult["success"] = True

    return finalResult


async def githubAPI(data):
    searchValue = data["searchTerm"]
    searchValue = [word for word in searchValue if word.lower() not in extraDetailedFluff]
    
    baseSearchURL = "https://api.github.com/search/repositories?per_page=5&accept=application/vnd.github.v3+json" + \
        "&q=" + "+".join(searchValue) + "+in:readme"
    print("Searching:", baseSearchURL)
    finalResult = {"humanData": [], 
                   "name": "github",
                   "success": False,
                   "specialKey": ""}

    headers = {"Authorization": f"token {githubKey}"}
    jsonResp = await request(baseSearchURL, headers)
    if jsonResp[0] != 200:
        for n, _ in enumerate(categoryList):
            try: categoryList[n]["apis"]["Github"]["status"] = False
            except KeyError: pass
        return finalResult
    else:
        jsonResp = jsonResp[1]
    
    packageNames = []
    if not jsonResp["incomplete_results"]:
        for item in jsonResp["items"]:
            baseReadmeURL = f"https://api.github.com/repos/{item['full_name']}/contents/README.md"
            overview = item["description"]
            packageNames.append(item["name"].lower())
            
            async with aiohttp.ClientSession() as session:
                async with session.get(baseReadmeURL, headers=headers) as fileInfoResp:
                    if fileInfoResp.status == 200:
                        fileInfo = await fileInfoResp.json()

                        async with session.get(fileInfo["download_url"], headers=headers) as readmeResp:
                            if readmeResp.status == 200:
                                readme = await readmeResp.text()
                                overview = readme.split("##", 1)[0]
                                overview = __md.convert(overview)
                                overview = re.sub(htmlCleaner, " ", overview)
                                overview = overview[:500]
                                
            title = f'{item["name"]} ({item["description"]})'
            finalResult["humanData"].append(
                {"url": item["html_url"], 
                 "title": title, 
                 "extract": overview})
        finalResult["success"] = True
    
    lookupKey = ""
    
    # Searches through the names of the packages found on github to try and exactly match one with one of the words in the search
    for word in searchValue:
        try: 
            packageNames.index(word.lower())
            lookupKey = word
            break
        except ValueError:
            continue
        
    finalResult["subject"] = lookupKey
    return finalResult


async def readthedocsAPI(data):
    searchValue = data["searchTerm"]
    subject = data["subject"]
    
    finalResult = {"humanData": [], 
                   "name": "readthedocs",
                   "success": False}
    
    if subject == "": return finalResult
    searchValue.remove(subject)
    baseSearchURL = "https://readthedocs.org/api/v2/search/" + "?project=" + subject + "&q=" + "+".join(searchValue) + "&version=latest"
    altSearchURL = "https://readthedocs.org/api/v2/search/" + "?project=" + subject + "&q=" + "+".join(searchValue) + "&version=master"
    print("Searching:", baseSearchURL)

    jsonResp = await request(baseSearchURL, {})
    if jsonResp[0] != 200:
        for n, _ in enumerate(categoryList):
            try: categoryList[n]["apis"]["ReadtheDocs"]["status"] = False
            except KeyError: pass
        return finalResult
    else:
        jsonResp = jsonResp[1]
    
    if jsonResp["count"] == 0:
        print("Searching:", altSearchURL)
        jsonResp = await request(altSearchURL, {})

        if jsonResp[0] != 200:
            return finalResult
        else:
            jsonResp = jsonResp[1]

    if jsonResp["results"] != []:
        for num, baseItem in enumerate(jsonResp["results"]):
            if num > 2: break
            for num, secondaryItem in enumerate(baseItem["blocks"]):
                if num > 2: break
                if "title" not in secondaryItem:
                    num -= 1
                    continue
                url = baseItem["domain"] + baseItem["path"]
                finalResult["humanData"].append({"url":url, 
                                    "title":secondaryItem["title"],
                                    "extract":secondaryItem["content"]})

            
        finalResult["success"] = True
    else:
        finalResult["success"] = False

    return finalResult


async def stackexchangeAPI(data):
    searchValue = data["searchTermMinimal"]
    baseSearchURL = "https://api.stackexchange.com/2.3/search/advanced?order=desc&answers=2&sort=votes&site=stackoverflow&filter=!T.hox84IXF3sIhYr(9i.Dh2kwYF9Tb" + \
                    "&q=" + "%20".join(searchValue)

    print("Searching:", baseSearchURL)
    finalResult = {"humanData": [], 
                   "name": "stackexchange",
                   "success": False}

    jsonResp = await request(baseSearchURL, {})
    if jsonResp[0] != 200:
        for n, _ in enumerate(categoryList):
            try: categoryList[n]["apis"]["StackExchange"]["status"] = False
            except KeyError: pass
        return finalResult
    else:
        jsonResp = jsonResp[1]
        
    print(f"Stackoverflow calls: {jsonResp['quota_remaining']}/{jsonResp['quota_max']}")
    for n1, question in enumerate(jsonResp["items"]):
        if n1 == 4:
            break
        answers = question["answers"]
        answers.sort(key=scoreBasedSort, reverse=True)
        for n2, answer in enumerate(answers):
            if n2 == 3:
                break
            body = __md.convert(answer["body_markdown"])
            body = html.unescape(body)
            title = html.unescape(question["title"])
            finalResult["humanData"].append({
                "title": title,
                "url": answer["link"],
                "extract": body,
                "score": answer["score"]
            })

    finalResult["success"] = True
    return finalResult


async def request(url, headers):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                jsonResp = await resp.json()
                return resp.status, jsonResp
    except aiohttp.ContentTypeError:
        return 403, {"success":False}
    except Exception:
        return 400, {"success":False}

async def asyncInit(apisToCall):
    """Intermediate between results and all APIs"""
    # This takes the list of APIs provided by the results method and runs all of them at the same time, collecting their results
    # this allows for highly efficient data collection
    return await asyncio.gather(*apisToCall)


async def redditAuth():
    """Oauth handler for reddit"""
    baseURL = "https://www.reddit.com/api/v1/access_token"
    data = {
        "grant_type": "client_credentials"
    }
    headers = {
        'User-Agent': userAgent,
        "Authorization": "Basic b1dSUG03ck1XeXJLWFhGUXM4M3BLZzpuSzMxaXVLLXlDd3BtTTVBSEZZX21SbnMtUjVtanc="
    }
    print("Authenticating with reddit")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(baseURL, data=data, headers=headers) as resp:
                jsonResp = await resp.json()

    except Exception:
        return {"Result": "Failed"}, 401

    if "access_token" in jsonResp:
        flask.session["redditToken"] = jsonResp["access_token"]
        return {"Result": "Success"}, 200
    else:
        return {"Result": "Failed"}, 401


def searchPreparation(value=None):
    """Prepared a string for searching by removing puncutation and unessential words"""
    if value == None:
        return
    value = value.strip()
    # removes all punctuation
    value = value.translate({ord(char): "" for char in string.punctuation})
    value = [word for word in value.split(
        " ") if word.lower() not in fluffWords]
    return value


def scoreBasedSort(e):
    """Sorts a list of dictionaries large to small based on a "score" key"""
    return int(e["score"])


@app.route("/search", methods=["POST"])
def search():
    """Mostly redundant, endpoint for setting category"""
    if flask.request.form["option"] == "0":  # If this post was setting the category, option is equal to 0
        flask.session["category"] = flask.request.form["value"]
    else:
        return {"response": "Failed, unknown search form"}, 400
    return {"response": "Success"}, 200


@app.route('/')
def home():
    """The homepage"""
    return flask.render_template("homepage.html", pageTitle="Foxfire")


@app.route('/results')
def results():
    """The results page, this also handles the system for initiating and collecting searches, same way other major search engines do it"""
    searchTerm = flask.request.args.get("search")
    # Decodes the url formatted search string to normal text
    searchTermOriginal = html.unescape(searchTerm)

    refinedAPIsToProbe = []
    criticalAPIsToCall = []
    offlineAPIs = 0
    criticalOfflineAPIs = 0
    finalResults = []
    APIsToProbe = []
    count = {"good": 0, "bad": 0}

    searchTermFiltered = searchPreparation(value=searchTermOriginal)
    # Some APIs prefer an even more stripped down version of the search, this is creating that
    searchTermExtraFiltered = [word for word in searchTermFiltered if word.lower() not in extraDetailedFluff]
    
    # If category = 0 its been set to "all" or a category hasn't been selected
    if "category" not in flask.session:
        flask.session["category"] = "0"

    if str(flask.session["category"]) == "0":
        for category in categoryList:
            for api in category["apis"].values():
                if api["runner"] not in [checkAPI["runner"] for checkAPI in APIsToProbe]:
                    APIsToProbe.append(api)                
    else:
        # Grabs the APIs to probe from the dictionary, all thats needed is the information not the name so just values are fetched
        APIsToProbe = categoryList[int(flask.session["category"])-1]["apis"].values()
    
    for api in APIsToProbe:
        # Makes sure the API is online and gets the most important APIs to call
        if api["status"]:
            if api["critical"]:
                criticalAPIsToCall.append(eval(api["runner"])({"searchTerm":searchTermFiltered, "searchTermMinimal":searchTermExtraFiltered}))
            else:
                refinedAPIsToProbe.append(api)
        elif api["status"] == False:
            if api["critical"]: criticalOfflineAPIs += 1
            offlineAPIs += 1
    
    criticalApiCollection = asyncio.run(asyncInit(criticalAPIsToCall))

    subject = [apiResult["subject"] for apiResult in criticalApiCollection if "subject" in apiResult]
    try: subject = subject[0]
    except IndexError: subject = ""

    apisToCall = [eval(api["runner"])({"searchTerm":searchTermFiltered, "subject":subject, "searchTermMinimal":searchTermExtraFiltered})
                  for api in refinedAPIsToProbe]
    apiCollection = asyncio.run(asyncInit(apisToCall))
    
    apiCollection = apiCollection + criticalApiCollection
    for apiResult in apiCollection:
        if apiResult["success"] == False:
            continue
        for num, result in enumerate(apiResult["humanData"]):
            extract = result["extract"]
            url = result["url"]
            title = result["title"]
            score = 50
            
            if len(title) >= 130:
                title = title[:130] + "..."
            if not extract or "may refer to:" in extract.lower():
                continue
            
            for word in searchTermExtraFiltered:
                if word.lower() not in extract.lower():
                    score -= 5
                score += extract.lower().count(word.lower()) * 5
                
            if subject.lower() in title.lower():
                score += 30
            if subject.lower() in extract.lower():
                score += 20
                
            if subject.lower() not in extract.lower() or subject.lower() not in title.lower():
                score -= 20

            # Prevents the extract from being over 4000 characters long
            modifiedExtract = extract[:4000]
            if modifiedExtract < extract:
                modifiedExtract += "..."

            # Awards points depending on the size of the extract.
            if len(modifiedExtract) <= 50:
                score -= 15
            elif len(modifiedExtract) <= 100 and len(modifiedExtract) > 50:
                score -= 10
            elif len(modifiedExtract) <= 1000 and len(modifiedExtract) > 500:
                score += 10
            elif len(modifiedExtract) >= 1000:
                score += 15

            score -= num*3

            if score >= 60:
                count["good"] += 1
            else:
                count["bad"] += 1

            finalResults.append(
                {"url": url, 
                 "base": apiResult["name"], 
                 "title": title, 
                 "extract": modifiedExtract, 
                 "score": score}
            )

    finalResults.sort(key=scoreBasedSort, reverse=True)
    return flask.render_template("results.html", pageTitle="Results", results=finalResults, count=count,
                                 uniqueWebsites=len(apiCollection), searchTerm=searchTerm, searchTermO=searchTermOriginal,
                                 offlineAPIs=offlineAPIs, criticalOfflineAPIs=criticalOfflineAPIs)


@app.route('/about')
def about():
    """About us page"""
    return flask.render_template("about.html", pageTitle="About")


@app.route('/contact', methods=["GET", "POST"])
def contact():
    """Contact us page"""
    
    if flask.request.method == "POST":
        # As the mail server uses SSL I need to initiate SSL
        context = ssl.create_default_context()
        contactersFirstname = flask.request.form.get("fName")
        contactersSurname = flask.request.form.get("sName")
        contactersEmail = flask.request.form.get("email")
        contactersSubject = flask.request.form.get("subject")
        contactersBody = flask.request.form.get("body")
        
        # Setting up the email
        message = multipart.MIMEMultipart("alternative")
        message["subject"] = contactersSubject
        message["From"] = contactersEmail
        message["To"] = "ollie@jakebot.co.uk"
        
        plaintextBody = f"""
        <html>
            <body>
                <b>Name:</b> <i>{contactersFirstname} {contactersSurname}</i><br>
                <b>Email:</b> <i>{contactersEmail}</i><br>
                <b>Subject:</b> <i>{contactersSubject}</i><br>
                <b>Body:</b><br>
                {contactersBody}<br>
            </body>
        </html>
        """
        mimeBody = text.MIMEText(plaintextBody, "html")
        message.attach(mimeBody)
        
        with smtplib.SMTP_SSL("jakebot.co.uk", 465, context=context) as server:
            server.login("foxfireollie@jakebot.co.uk", emailPassword)
    
            server.sendmail(contactersEmail, "ollie@jakebot.co.uk", message.as_string()) 
        
        return {"Response":"Success"}, 200
    
    return flask.render_template("contact.html", pageTitle="Contact Us")


@app.route('/api/ping', methods=["GET", "POST"])
async def APIPing():
    apiName = flask.request.form["api"]
    time1 = asyncio.get_event_loop().time()

    for n, _ in enumerate(categoryList):
        try: 
            baseURL = categoryList[n]["apis"][apiName]["baseURL"]
            break
        except KeyError: pass
  
    async with aiohttp.ClientSession() as session:
        async with session.get(baseURL) as resp:
            latency = round((asyncio.get_event_loop().time() - time1) * 1000)
            
    for n, _ in enumerate(categoryList):
        try: categoryList[n]["apis"][apiName]["ping"] = latency
        except KeyError: pass
    
    return {"latency": latency}, 200


async def statusChecker():
    """Runs every 10 minutes and pings each server to see if its online or not"""
    for n, cat in enumerate(categoryList):
        for key in cat["apis"]:
            api = cat["apis"][key]
            baseURL = api["baseURL"]
            if api["status"] == None:
                continue
            try:
                time1 = asyncio.get_event_loop().time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(baseURL) as resp:

                        if resp.status != 200:
                            categoryList[n]["apis"][key]["status"] = False
                        else:
                            categoryList[n]["apis"][key]["status"] = True
                            categoryList[n]["apis"][key]["ping"] = round(
                                (asyncio.get_event_loop().time() - time1)*1000)

            except Exception as e:
                categoryList[n]["apis"][key]["status"] = False

@app.route('/api/dashboard')
def apiDashboard():
    """Where all the APIs can be viewed with status and ping information"""
    statuses = {"total": 0, "offline": 0, "online": 0}
    
    
    for cat in categoryList:
        statuses["offline"] += sum(api["status"] == False for api in cat["apis"].values())
        statuses["online"] += sum(api["status"] == True for api in cat["apis"].values())
        
        statuses["total"] += len(cat["apis"])

    return flask.render_template("apiStatus.html", pageTitle="Api Status Dashboard", categoryList=categoryList, apiStatuses=statuses)


@app.errorhandler(404)
def notfound(_):
    """Error 404 page!"""
    return flask.render_template("404.html", pageTitle="Uh Oh- Thats a 404!")


def statusIntermediate():
    """Used to run the require asyncio code as it cant be directly run from scheduler.add_job"""
    asyncio.run(statusChecker())


statusIntermediate()  # Runs the status finder immediately
# Then "pledges" to run the status finder system every 10 minutes
scheduler.add_job(func=statusIntermediate, trigger="interval", seconds=600)
scheduler.start()

# this gets run when the project is being run locally not on a server, hence when its being developed
if __name__ == "__main__":
    website_url = "localhost:5000"
    app.config["SERVER_NAME"] = website_url
    # Fixing a bug that occurs only in windows so will only appear during bug testing
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app.run(debug=True, use_reloader=False)
