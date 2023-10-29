//共通パーツ読み込み
fetch('detail_header.html').then(response => response.text()).then(data => {
  document.getElementById('header').innerHTML = data;
}).catch(e=> {console.log(e)})