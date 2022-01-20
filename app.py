import urllib.parse as urllib
from apscheduler.schedulers.background import BackgroundScheduler
import flask, string, asyncio, aiohttp, markdown, re, bleach, html #FoxFire99
from flask import request
# https://stackapps.com/apps/oauth/view/22587

app = flask.Flask(__name__, static_folder='static', static_url_path="")
wolframID = "E5XQJP-AR8P58K4HL"
app.secret_key = "160DA98BE181F8F67DCD9B74FC16AEB2G5C8D667C62DE99139B4A1Z84189DFA5" # Encryption key for the browser session
app.config["SERVER_NAME"] = "www.foxfire.fyi"
app.config["PREFERRED_URL_SCHEME"] = "https"
userAgent = "webApp:oWRPm7rMWyrKXXFQs83pKg:v1.0.0 (by /u/OliMations)"
scheduler = BackgroundScheduler()
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
CLEANR = re.compile('<.*?>') 

categoryList = [{"name":"Standard", "id":1, "apis":[ # Defines all the categorys and their APIs
    {"name":"WolframAlpha ★", "logo":"wolfram.jpg", "runner":"wolframAPI", "baseURL":"https://api.wolframalpha.com", "ping":0, "status":True, "desc":"WolframAlpha is a computational knowledge engine. It answers factual queries directly by computing the answer from externally sourced data."},
    {"name":"Wikipedia", "logo":"wikimedia.png", "runner":"wikimediaAPI", "baseURL":"https://en.wikipedia.org", "ping":0, "status":True, "desc":"Wikimedia is the foundation that hosts the worlds most popular online encyclopedia, Wikipedia, among other important services."},
    {"name":"Reddit", "logo":"reddit.png", "runner":"redditAPI", "baseURL":"https://reddit.com", "ping":0, "status":True, "desc":"Reddit is a social news aggregation, web content rating, and discussion website. Registered members submit content to the site such as links, text posts, images, and videos, which are then voted up or down by other members."}
]}, {"name":"Programming", "id":2, "apis":[
    {"name":"Reddit", "logo":"reddit.png", "runner":"redditAPI", "baseURL":"https://reddit.com", "ping":0, "status":True, "desc":"Reddit is a social news aggregation, web content rating, and discussion website. Registered members submit content to the site such as links, text posts, images, and videos, which are then voted up or down by other members."},
    {"name":"Stack Exchange", "logo":"stackexchange.png", "runner":"stackexchangeAPI", "baseURL":"https://api.stackexchange.com", "ping":0, "status":True, "desc":"Stack Exchange is a network of question-and-answer websites (including stack overflow) on topics in diverse fields, each site covering a specific topic."}
]}]
fluffWords = ["to", "and", "but", "are", "how", "is", "do", "my", "i", "on", "or", "would", "when", "with", "the", "by", "as", 
    "what", "a", "an", "of", "it", "for", "that", "from", "there", "who", "can", "have"]


async def wolframAPI(searchValue, *_):
    baseURL = "https://api.wolframalpha.com/v2/query" + "?appid=" + wolframID + "&output=json" + "&format=plaintext"
    finalURL = baseURL + "&input=" + "%20".join(searchValue)
    print("Collating:", finalURL)

    finalResult = {"success":True, "name":"Wolfram:Alpha", "humanData":[]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(finalURL) as resp:
                jsonResp = await resp.json()
    except aiohttp.ClientConnectorCertificateError:
        finalResult["success"] = False
        return finalResult

    url = "https://www.wolframalpha.com/input/?i=" + "%20".join(searchValue)
    if "pod" in jsonResp:
        for pod in jsonResp["queryresult"]["pods"]:
            if "subpods" in pod:
                for subpod in pod["subpods"]:
                    if "plaintext" in subpod and len(subpod["plaintext"]) > 20:
                        finalResult["humanData"].append({"extract":subpod["plaintext"].replace("\n", " "), "url":url, "title":" ".join(searchValue)})


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

async def redditAPI(searchValue, *_):
    if "redditToken" not in flask.session:
        result = await redditAuth()
        if 200 not in result:
            return {"success":False}
    
    baseURL = "https://oauth.reddit.com/"
    finalURL = baseURL + "search?type=link&sort=relevance&limit=5" + "&q=" + "%20".join(searchValue)
    print("Collating:", finalURL)

    headers = {
        'User-Agent': userAgent,
        'Authorization': f"bearer {flask.session['redditToken']}"
    }

    finalResult = {"success":True, "name":"Reddit", "humanData":[]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(finalURL, headers=headers) as resp:
                try: jsonResp = await resp.json()
                except aiohttp.ContentTypeError:
                    del flask.session["redditToken"]
                    return await redditAPI(searchValue=searchValue)
    except aiohttp.ClientConnectorCertificateError:
        finalResult["success"] = False
        return finalResult

    
    for child in jsonResp["data"]["children"]:
        if int(child["data"]["num_comments"]) > 1:
            finalURL = baseURL + "r/" + child["data"]['subreddit'] + "/comments/" + child["data"]["name"].split("_", 1)[-1] + "?sort=top&depth=0&limit=5"
            async with aiohttp.ClientSession() as session:
                async with session.get(finalURL, headers=headers) as resp:
                    jsonResp2 = await resp.json()
                    for commentChild in jsonResp2[1]["data"]["children"]:
                        if "body" in commentChild["data"]:
                            try: title = jsonResp2[0]["data"]["children"][0]["data"]["title"]
                            except: title = "Unknown"
                            body = markdown.markdown(commentChild["data"]["body"])
                            
                            body = html.unescape(body).replace("<br>", "\n")

                            body = re.sub(CLEANR, '', body)
                            finalResult["humanData"].append({"extract":body, "title":title, "url":f'https://www.reddit.com{commentChild["data"]["permalink"]}', 
                            "score":commentChild["data"]["score"]})

    return finalResult

async def wikimediaAPI(searchValue, *_):
    baseSearchURL = "https://en.wikipedia.org/w/api.php?action=query&list=prefixsearch&format=json" + "&pssearch=" + "%20".join(searchValue)
    print("Searching:", baseSearchURL)
    finalResult = {"success":False, "humanData":[], "name":"Wikipedia"}

    try: 
        async with aiohttp.ClientSession() as session:
            async with session.get(baseSearchURL) as resp:
                jsonResp = await resp.json()
                searchResults = [result["pageid"] for result in jsonResp["query"]["prefixsearch"] if "(" not in result["title"]]
    except aiohttp.ClientConnectorCertificateError:
        finalResult["success"] = False
        return finalResult

    for pageid in searchResults:
        baseURl = "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&exsectionformat=wiki&format=json" + "&pageids=" + str(pageid)
        print("Collating:", baseURl)

        async with aiohttp.ClientSession() as session:
            async with session.get(baseURl) as resp:
                jsonResp = await resp.json()
        
        for num, result in enumerate(jsonResp["query"]["pages"]):
            if num >= 4: break
            title = jsonResp["query"]["pages"][result]["title"]
            accessURL = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
            extract = jsonResp["query"]["pages"][result]["extract"]
            extract = re.sub(r"==.*?==", " ", extract).replace("\n", "").replace("\\", "")
            finalResult["humanData"].append({"url": accessURL, "title":title, "extract": extract})
    
    finalResult["success"] = True

    return finalResult

async def stackexchangeAPI(searchValue, *_):
    baseSearchURL = "https://api.stackexchange.com/2.3/search/advanced?order=desc&answers=1&sort=votes&site=stackoverflow&filter=!T.hox84IXF3sIhYr(9i.Dh2kwYF9Tb" + "&q=" + "%20".join(searchValue)
    print("Searching:", baseSearchURL)
    finalResult = {"humanData":[], "name":"stackexchange"}

    try: 
        async with aiohttp.ClientSession() as session:
            async with session.get(baseSearchURL) as resp:
                jsonResp = await resp.json()
                print(resp.status)
    except aiohttp.ClientConnectorCertificateError:
        finalResult["success"] = False
        return finalResult

    print(f"Stackoverflow calls: {jsonResp['quota_remaining']}/{jsonResp['quota_max']}")
    for n1, question in enumerate(jsonResp["items"]):
        if n1 == 4: break
        answers = question["answers"]
        answers.sort(key=scoreBasedSort, reverse=True)
        for n2, answer in enumerate(answers):
            if n2 == 3: break
            body = markdown.markdown(answer["body_markdown"])
            body = html.unescape(body)
            body = bleach.clean(body, tags=["br", "strong", "em", "a"], strip=True)
            finalResult["humanData"].append({
                "title": html.unescape(question["title"]),
                "url": answer["link"],
                "extract": body,
                "score": answer["score"]
            })
        
    finalResult["success"] = True

    return finalResult

async def asyncInit(apisToCall):
    return await asyncio.gather(*apisToCall)

async def redditAuth():
    baseURL = "https://www.reddit.com/api/v1/access_token"
    data = {
        "grant_type":"client_credentials"
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
                print(jsonResp)

    except aiohttp.ClientConnectorCertificateError:
        return {"Result":"Failed"}, 401

    if "access_token" in jsonResp: 
        flask.session["redditToken"] = jsonResp["access_token"]
        return {"Result":"Success"}, 200
    else:
        return {"Result":"Failed"}, 401

def searchPreparation(value=None):
    "Prepared a string for searching by removing puncutation and unessential words"
    if value == None: return
    value = value.translate({ord(char):"" for char in string.punctuation})
    value = [word for word in value.split(" ") if word.lower() not in fluffWords]
    return value

def scoreBasedSort(e):
    return int(e["score"])

@app.route("/search", methods=["POST"])
def search():
    if request.form["option"] == "0": # If this post was setting the category, option is equal to 0
        flask.session["category"] = request.form["value"]   
    else:
        return {"response":"Failed, unknown search form"}, 400
    return {"response":"Success"}, 200


@app.route('/')
def home():
    return flask.render_template("homepage.html", pageTitle="Foxfire")

@app.route('/results')
def results():
    searchTerm = request.args.get("search")
    searchTermOriginal = urllib.unquote(searchTerm)
    
    searchTermFiltered = searchPreparation(value=searchTermOriginal)
    if flask.session["category"] == 0: return {"response":"Failed, automatic cat switching not implemented yet"}

    apisToCall = [eval(api["runner"])(searchTermFiltered, searchTermOriginal) for api in categoryList[int(flask.session["category"])-1]["apis"] if api["status"]]
    apiCollection = asyncio.run(asyncInit(apisToCall))
    # apiCollection = []

    finalResult = []
    count = {"good":0, "bad":0}
    print(apiCollection)
    for apiResult in apiCollection:
        if apiResult["success"] == False: continue
        for num, result in enumerate(apiResult["humanData"]):
            extract = result["extract"]
            url = result["url"]
            title = result["title"]
            score = 100
            if " ".join(searchTermFiltered).lower() not in extract: score -= 10

            modifiedExtract = extract[:4000]
            if modifiedExtract < extract: modifiedExtract += "..."
            
            if "may refer to:" in modifiedExtract.lower(): continue

            if len(modifiedExtract) <= 50: score -= 30
            elif len(modifiedExtract) <= 100: score -= 20
            elif len(modifiedExtract) <= 500: score -= 10
            elif len(modifiedExtract) <= 1000: score -= 5

            score -= num*3
        
            if score >= 70: count["good"] += 1
            else: count["bad"] += 1

            finalResult.append({"url":url, "base":apiResult["name"], "title":title, "extract":modifiedExtract, "score":score})
    
    finalResult.sort(key=scoreBasedSort, reverse=True)
    return flask.render_template("results.html", pageTitle="Results", results=finalResult, count=count, 
    uniqueWebsites=len(apiCollection), searchTerm=searchTerm)

@app.route('/about')
def about():
    return flask.render_template("about.html", pageTitle="About")

@app.route('/contact')
def contact():
    return flask.render_template("contact.html", pageTitle="Contact Us")

async def statusChecker():
    for n, cat in enumerate(categoryList):
        for n2, api in enumerate(cat["apis"]):
            baseURL = api["baseURL"]
            if api["status"] == None: continue
            try:
                time1 = asyncio.get_event_loop().time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(baseURL) as resp:
                        
                        if resp.status != 200:
                            categoryList[n]["apis"][n2]["status"] = False
                        else:
                            categoryList[n]["apis"][n2]["status"] = True
                            categoryList[n]["apis"][n2]["ping"] =round((asyncio.get_event_loop().time() - time1)*1000)
            except Exception as e:
                categoryList[n]["apis"][n2]["status"] = False

                
@app.route('/api/dashboard')
def apiDashboard():
    statuses = {"total":0, "offline":0, "online":0}
    for cat in categoryList:
        statuses["total"] += len(cat["apis"])
        for api in cat["apis"]:

            if not api["status"]:
                statuses["offline"] += 1
            elif api["status"]:
                statuses["online"] += 1

    return flask.render_template("apiStatus.html", pageTitle="Api Status Dashboard", categoryList=categoryList, apiStatuses=statuses)

@app.errorhandler(404)
def notfound(_):
    return flask.render_template("404.html", pageTitle="Uh Oh- Thats a 404!")

def statusIntermediate():
    asyncio.run(statusChecker())

statusIntermediate()
scheduler.add_job(func=statusIntermediate, trigger="interval", seconds=300)
scheduler.start()

if __name__ == "__main__":
    website_url = "localhost:5000"
    app.config["SERVER_NAME"] = website_url
    app.run(debug=True, use_reloader=False)
