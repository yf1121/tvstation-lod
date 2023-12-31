# テレビ局LOD（Ver.1.2）

テレビ局LODは、地上波テレビ局及びNHK地上波放送を対象として基礎データを一つのオープンデータとして構築する試みです。WikipediaやWikidataのデータを活用し、欠損データは適宜手作業で各放送局のサイト等を調べて構築しています。放送番組の識別子を研究として扱っており、その過程の中でテレビ局LODを考案しました。このデータによって、テレビ局を用いたアプリケーション開発に役立つことが期待されます。

このデータはほかのデータと組み合わせられる可能性を高めるために、構築しているデータの全容はTurtleファイルとして公開し、機械から読み取りやすい形式となっています。別にFusekiのツールに取り込むことで、どなたでもSPARQLでクエリを実行できます。現在は地上波のみですが、衛星放送や民間放送のラジオについても拡張していくことを想定し、スキーマ設計を行っています。また、利用しやすいようにSchema.orgの共通語彙をなるべく使うように心がけています。

- [https://w3id.org/tvstationjp/](https://w3id.org/tvstationjp/)

### 利用しているオープンデータ

- Wikipedia : 名称、開局年月日、呼出名称等
- Wikidata : WikidataのページのID
- DBpedia : DBpediaのページURL、局ロゴの画像ファイルURL

### スキーマ情報

- SchemaInfo.xlsxを参照してください。

### ライセンス

This work © 2023 by yufiny is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.ja)