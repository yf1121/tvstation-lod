import os
import re
import requests
import time
import urllib.parse

baseUrl = "https://w3id.org/tvstationjp"
website_name = "テレビ局LOD"
dir_path = "."
data = {}

# 述語のPREFIXに置換する語彙リスト
v_prefixes = {
  "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
  "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
  "https://schema.org/": "schema:",
  "https://w3id.org/tvstationjp/tvst/": "tvst:",
  "http://www.wikidata.org/prop/direct/": "wdt:",
}

# 述語の説明
verbs_desc = {
  "<http://www.w3.org/2000/01/rdf-schema#label>": "名称",
  "<http://www.w3.org/2000/01/rdf-schema#comment>": "解説",
  "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>": "基本区分",
  "<https://schema.org/description>": "説明",
  "<https://schema.org/containsPlace>": "含まれる地域",
  "<https://schema.org/areaServed>": "放送対象となる地域",
  "<https://schema.org/name>": "略称",
  "<https://schema.org/alternateName>": "その他の別名/愛称",
  "<https://schema.org/formerName>": "かつての呼称",
  "<https://w3id.org/tvstationjp/tvst/keystation>": "キー局",
  "<https://schema.org/url>": "公式ウェブサイト",
  "<https://schema.org/foundingDate>": "発足年月日",
  "<https://schema.org/logo>": "ロゴ",
  "<http://www.wikidata.org/prop/direct/P3225>": "法人番号",
  "<https://w3id.org/tvstationjp/tvst/networkBlock>": "地域ブロック",
  "<https://w3id.org/tvstationjp/tvst/newsNetwork>": "ニュース系列",
  "<https://w3id.org/tvstationjp/tvst/networkSystem>": "番組供給系列",
  "<https://w3id.org/tvstationjp/tvst/callName>": "呼出名称",
  "<https://w3id.org/tvstationjp/tvst/beginningDate>": "開局年月日",
  "<https://w3id.org/tvstationjp/tvst/platform>": "プラットフォーム",
  "<https://w3id.org/tvstationjp/tvst/chPosition>": "リモコンキーID",
  "<https://w3id.org/tvstationjp/tvst/parentStation>": "親局",
  "<https://w3id.org/tvstationjp/tvst/parentDTVCh>": "デジタル親局チャンネル",
  "<https://w3id.org/tvstationjp/tvst/parentATVCh>": "アナログ親局チャンネル",
  "<https://w3id.org/tvstationjp/tvst/logicalCh>": "論理チャンネル",
  "<https://schema.org/ownershipFundingInfo>": "親会社（放送持株会社）",
  "<https://schema.org/parentOrganization>": "上位組織",
  "<https://schema.org/brand>": "所有しているチャンネル",
  "<https://schema.org/address>": "郵便番号",
  "<https://schema.org/latitude>": "緯度",
  "<https://schema.org/longitude>": "経度",
  "<http://www.wikidata.org/prop/direct/P159>": "所在地",
  "<http://www.wikidata.org/prop/direct/P2317>": "呼出符号",
  "<https://schema.org/sameAs>": "関連リンク",
}

# 行を三つ組に分割するメソッド
#   引数: 1行文字列
#   返り値: 配列, 末尾の区切り文字
def mitsugumi(line):
  line_ary = []
  point = "."
  index = 0
  isBlock = False
  for letter in line:
    # 区切り地点の場合
    if isBlock == False and re.match(r'\s', letter):
      if len(line_ary) > index and len(line_ary[index]) > 0:
        index += 1
      continue
    elif isBlock == False and re.match(r'<|"', letter):
      isBlock = letter
    elif isBlock == "<" and re.match(r'>', letter):
      isBlock = False
    elif isBlock == "\"" and re.match(r'"', letter):
      isBlock = False
    elif isBlock == False and re.match(r'\.|;|\,', letter):
      point = letter
      break
    # データ部分の場合
    if len(line_ary) <= index:
      line_ary.append("")
    line_ary[index] += letter
  return line_ary, point

# Turtle Fileを読み込むメソッド
#   引数: lines
#   返り値: なし
def getTtl(lines, u_data):
  update_data = u_data
  prefixes = {}
  prev_line = []
  for line in lines:
    if not line:
      break
    else:
      line = line.strip()
    
    line_ary, point = mitsugumi(line)
    line_ary = prev_line + line_ary

    # @PREFIXで始まる場合
    if len(line_ary) > 2 and line_ary[0] == "@prefix":
      prefixes[line_ary[1]] = line_ary[2]
      continue

    # prefixの置換
    for str in line_ary:
      m = re.search(r'^[^<>]+?\:', str)
      if m is not None and m.group() in prefixes:
        line_ary[line_ary.index(str)] = str.replace(m.group(), prefixes[m.group()].replace(">", "")) + ">"

    # JSONに格納
    if line_ary[0] not in update_data:
      update_data[line_ary[0]] = {}
    if line_ary[1] not in update_data[line_ary[0]]:
      update_data[line_ary[0]][line_ary[1]] = []
    if line_ary[2] not in update_data[line_ary[0]][line_ary[1]]:
      update_data[line_ary[0]][line_ary[1]].append(line_ary[2])
  
    # 次の行への引継ぎ
    if point == ";" and len(line_ary) > 1:
      prev_line = [line_ary[0]]
    elif point == "," and len(line_ary) > 1:
      prev_line = [line_ary[0], line_ary[1]]
    else:
      prev_line = []
  return update_data

# URIからデータを取得するメソッド
#   引数: URI
#   返り値: ラベル
def getUriInfo(uri, u_data):
  update_data = {}
  if uri in u_data:
    update_data[uri] = u_data[uri]
  else:
    update_data[uri] = {}

    # URIからデータを取得する
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100',
      'Content-Type': 'text/turtle'
    }
    url = re.sub(r"^<|>$", "", uri)
    # 統計LODの地域URIの場合はSPARQLを実行して取得する
    if re.search(r"data\.e\-stat\.go\.jp/lod/", uri) is not None:
      sel = "select ?v ?o \nwhere {\n"+uri+" ?v ?o .}"
      url = "http://data.e-stat.go.jp/lod/sparql/alldata/query?query=" + urllib.parse.quote(sel)
      r = requests.post(url, headers=headers, timeout=30)
      time.sleep(3)
      for e in r.json()["results"]["bindings"]:
        O_data = e["O"]["value"]
        if e["O"]["type"] == "uri":
          O_data = "<" + O_data + ">"
        if e["V"]["type"] == "uri":
          if "<" + e["V"]["value"] + ">" in update_data[uri]:
            update_data[uri]["<" + e["V"]["value"] + ">"].append(O_data)
          else:
            update_data[uri]["<" + e["V"]["value"] + ">"] = [O_data]
  return update_data

# 指定された言語ラベルを返すメソッド
#   引数: 配列
#   返り値: 文字列
def returnLangStr(array, lang):
  str = re.sub(re.compile("^\"|\"@?\w*?$"), '', array[0])
  for elem in array:
    if elem.endswith("\"@"+lang):
      str = re.sub(re.compile("^\"|\"@({})$".format(re.escape(lang))), '', elem)
      break
    elif lang == "ja" and re.search(r"^[ぁ-んァ-ヶー一-龯\s]+$", elem) is not None:
      if re.search(r"^[ぁ-んァ-ヶー\s]+$", elem) is not None:
        if re.search(r"^[ぁ-んァ-ヶー一-龯\s]+$", str) is not None:
          continue
      str = re.sub(re.compile("^\"|\"@({})$".format(re.escape(lang))), '', elem)
    elif lang == "en" and re.search(r"^\w+$", elem) is not None:
      str = re.sub(re.compile("^\"|\"@({})$".format(re.escape(lang))), '', elem)
  return str

#############################
### ここからメインプロセス ###
#############################

# .ttlファイルのリストを取得する
files = [
  f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f) ) and f.endswith(".ttl")
]

# データの読み込み
for path in files:
  # ttlファイルを開く
  with open(path, 'r', encoding='UTF-8') as f:
    lines = []
    while True:
      line = f.readline()
      if not line:
        break
      else:
        lines.append(line)
    data.update(getTtl(lines, data))
    # break

# HTMLテン=プレートの読み込み
html_temp = ""
html_jstemp = ""
header_html = ""
with open("./templates/detail.html", 'r', encoding='UTF-8') as f:
  html_temp = f.read() 
with open("./templates/detail_header.html", 'r', encoding='UTF-8') as f:
  header_html = f.read().replace("./", "../templates/")

# 個別HTMLとTurtleデータの書き出し
updt_data = {}
updt_data.update(data)
for s in data:
  print("\t処理中: " + s)
  if re.search(re.compile("^<({})".format(re.escape(baseUrl))), s) is None:
    continue
  ttl = ""
  ttl += s + " "
  pathname = s.replace(baseUrl, ".").replace("<", "").replace(">", "")

  # リンクのツリー部分を生成
  path_str = baseUrl
  tree = ""
  for path in pathname.split("/"):
    if path == ".":
      tree += "<a href=\"" + path_str + "\">" + website_name + "</a>"
    else:
      path_str += "/" + path
      tree += " / <a href=\"" + path_str + "\">" + path + "</a>"
  # パーマリンクの用意
  name = re.search(r"/[\w\-\_]*?$", pathname)
  if name is not None:
    name = name.group().replace("/", "")
  table = ""
  label_str = ""
  englabel = ""

  ### === 述語の処理 === ###
  verb_count = 0
  for v in data[s]:
    # ttlファイル
    ttl += v + " "
    # HTMLファイル
    table += "<tr>\n<th>"
    if v.startswith("<") and v.endswith(">"):
      table += "<a href='" + v.replace("<", "").replace(">", "") + "'>"
      a_link = ""
      for prefix_before in v_prefixes:
        if re.search(re.compile("^<({})".format(re.escape(prefix_before))), v) is not None:
          a_link += re.sub(re.compile("^<({})".format(re.escape(prefix_before))), v_prefixes[prefix_before], v.replace(">", ""))
          break
      if a_link == "":
        a_link += re.sub(r"^<|>$", "", v)
      if v in verbs_desc:
        table += verbs_desc[v] + "</a><a class='verb_uri' href='"
        table += v.replace("<", "").replace(">", "") + "'>" + a_link +"</a>"
      else:
        table += a_link + "</a>"
    else:
      table += v
    table += "</th>\n<td>"

    ### === 目的語の処理 === ###
    for o in data[s][v]:
      # ttlファイル
      if len(data[s][v]) > data[s][v].index(o) + 1:
        ttl += o + ",\n\t\t"
      elif len(data[s]) > verb_count + 1:
        ttl += o + ";\n\t"
      else:
        ttl += o + ".\n"
      
      # HTMLファイル
      table += "<p>"
      if o.startswith("<") and o.endswith(">"):
        # URL
        updt_data.update(getUriInfo(o, updt_data))
        if "<http://data.e-stat.go.jp/lod/terms/sacs#latestCode>" in updt_data[o]:
          updt_data.update(getUriInfo(updt_data[o]["<http://data.e-stat.go.jp/lod/terms/sacs#latestCode>"][0], updt_data))
        o_uri = o.replace("<", "").replace(">", "")
        # ロゴURLの場合
        if v == "<https://schema.org/logo>":
          table += "<a href='" + o_uri + "'><img src='"
          table += o_uri + "' style='width: 150px;' /></a></p><p>"
          table += "<a class='resource_uri' href='" + o_uri + "'>" + o_uri + "</a>"
        # Wikipediaリンクの場合
        elif re.search(r"^https?\:\/\/ja\.wikipedia\.org|^https?\:\/\/ja\.dbpedia\.org|^https?\:\/\/www\.wikidata\.org", o_uri) is not None:
          if "ja.wikipedia" in o_uri:
            table += "<a class='wiki_link' href='" + o_uri + "'><span class='wiki_name'>Wikipedia 日本語版</span><span class='resource_uri'>"
          elif "ja.dbpedia" in o_uri:
            table += "<a class='wiki_link' href='" + o_uri + "'><span class='wiki_name'>DBpedia 日本語版</span><span class='resource_uri'>"
          elif "wikidata" in o_uri:
            table += "<a class='wiki_link' href='" + o_uri + "'><span class='wiki_name'>WIKIDATA</span><span class='resource_uri'>"
          wiki_entity = re.search(r"\/\w+?\/?$", o_uri)
          if wiki_entity is not None:
            table += wiki_entity.group().replace("/", "") + "</span></a>"
        else:
          table += "<a href='" + o_uri + "'>"
          if "<http://www.w3.org/2000/01/rdf-schema#label>" in updt_data[o]:
            table += "<span>" + returnLangStr(updt_data[o]["<http://www.w3.org/2000/01/rdf-schema#label>"], "ja") + "</span></a>"
            region_code = o_uri.replace("http://data.e-stat.go.jp/lod/sac/", "sac:")
            table += "<a class='resource_uri' href='" + o_uri + "'>" + region_code
          # 統計LODの地域コードの場合
          elif "<http://data.e-stat.go.jp/lod/terms/sacs#latestCode>" in updt_data[o]:
            latestCode = updt_data[o]["<http://data.e-stat.go.jp/lod/terms/sacs#latestCode>"][0]
            if "<http://www.w3.org/2000/01/rdf-schema#label>" in updt_data[latestCode]:
              table += "<span>" + returnLangStr(updt_data[latestCode]["<http://www.w3.org/2000/01/rdf-schema#label>"], "ja") + "</span>"
            region_code = o_uri.replace("http://data.e-stat.go.jp/lod/sac/", "sac:")
            table += "<a class='resource_uri' href='" + o_uri + "'>" + region_code
          else:
            # その他のURL
            table += o_uri
          table += "</a>"
      else:
        # 文字列
        o_str = re.sub(r"^\"|\"@?[\w\-]*?$", "", o)
        o_lang = re.search(r"@?[\w\-]*?$", o)
        # 日本語ラベルであればページのタイトルとして使用する
        if v == "<http://www.w3.org/2000/01/rdf-schema#label>" and o.endswith("@ja"):
          label_str = o_str
        # 英語ラベルであれば英語ラベルとして使用する
        if v == "<http://www.w3.org/2000/01/rdf-schema#label>" and o.endswith("@en"):
          englabel = o_str
        if v == "<http://www.wikidata.org/prop/direct/P3225>":
          # 法人番号の場合
          table += "<a href='https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=" + o_str + "'>" + o_str + "</a>"
        else:
          table += o_str
        if o_lang is not None:
          table += "<span class='langtag'>" + o_lang.group() + "</span>"
      table += "</p>"
    table += "</td>\n</tr>"
    verb_count += 1
  html = html_temp.format(
    header=header_html, baseUrl=baseUrl, website=website_name, tree=tree, label=label_str, englabel=englabel,
    permalink=s.replace("<", "").replace(">", ""), table=table, page_script=html_jstemp
  )

  # URIに応じてディレクトリを用意して保存する
  dir = re.sub(r"/[\w\-\_]*?$", '', pathname, 1)
  os.makedirs(dir, exist_ok=True)
  # ttl File
  with open(pathname + ".ttl", 'w', encoding='UTF-8') as f:
    f.write(ttl)
  # html File
  with open(pathname + ".html", 'w', encoding='UTF-8') as f:
    f.write(html)