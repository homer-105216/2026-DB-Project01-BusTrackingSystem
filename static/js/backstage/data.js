// 後台欄位設定、示範資料與 localStorage；尚未串接 SQL。
// 欄位對應組內關聯綱目；SQL 尚未提供，目前以瀏覽器資料展示操作。
const configs={
routes:{title:'路線管理',group:'CMS / 資料管理',desc:'維護路線名稱與起訖站，建立公車服務的基礎資料。',fields:[['routeId','路線編號'],['routeName','路線名稱'],['origin','起點'],['destination','終點']]},
stations:{title:'站點管理',group:'CMS / 資料管理',desc:'維護站牌名稱、地址與地理座標。',fields:[['stationId','站點編號'],['sName','站點名稱'],['address','地址'],['sLatitude','緯度','number'],['sLongitude','經度','number']]},
stops:{title:'路線站序與去返程',group:'SCHEDULE / 班表調度',desc:'先選擇路線，再查看與設定去程、返程的停靠站順序。',fields:[['routeId','路線','ref:routes:routeId:routeName'],['stationId','站點','ref:stations:stationId:sName'],['rDirection','行駛方向','select:去程,返程'],['stopSequence','站序','positive']]},
'bus-types':{title:'車型管理',group:'CMS / 資料管理',desc:'管理 Bus_Type 車型與載客容量，供車輛資料選用。',fields:[['busType','車型名稱'],['capacity','載客容量','positive']]},
buses:{title:'車輛管理',group:'CMS / 資料管理',desc:'以車牌號碼識別車輛，每輛車選擇一種車型，容載人數由車型自動帶入。',fields:[['bId','車牌號碼'],['busType','車型','ref:bus-types:busType:busType']]},
trips:{title:'預定班次管理',group:'SCHEDULE / 班表調度',desc:'先選擇路線，再分別管理去程與返程的預定發車班次。',fields:[['tId','班次編號'],['routeId','路線','ref:routes:routeId:routeName'],['departureTime','發車時間','time'],['tDirection','行駛方向','select:去程,返程']]},
dispatch:{title:'每日派車與司機安排',group:'SCHEDULE / 班表調度',desc:'為每日班次指派車輛、司機，並維護執行狀態。',fields:[['tId','預定班次','ref:trips:tId:tId'],['date','執行日期','date'],['driver','司機'],['status','執行狀態','select:未發車,執行中,已完成,已取消'],['bId','車輛','ref:buses:bId:bId']]},
'stop-times':{title:'各站預計到離站時間',group:'SCHEDULE / 班表調度',desc:'依班次設定各停靠站預計到站及離站時間。',fields:[['tId','班次','ref:trips:tId:tId'],['stationId','站點','ref:stations:stationId:sName'],['expArrivalTime','預計到站','time'],['expDepartureTime','預計離站','time']]}
};
const seeds={routes:[['R001','紅線 01','高雄車站','中山大學'],['R002','藍線 02','左營高鐵站','美麗島站']],stations:[['S001','高雄車站','高雄市三民區建國二路',22.639,120.302],['S002','美麗島站','高雄市新興區中山一路',22.631,120.301],['S003','中山大學','高雄市鼓山區蓮海路70號',22.626,120.266]],stops:[['R001','S001','去程',1],['R001','S002','去程',2],['R001','S003','去程',3],['R001','S003','返程',1],['R001','S001','返程',2]],'bus-types':[['電動低地板公車',40],['大型柴油公車',45]],buses:[['EAA-1234','電動低地板公車'],['KAB-5678','大型柴油公車']],trips:[['T001','R001','08:00','去程'],['T002','R001','09:00','返程'],['T003','R002','08:30','去程']],dispatch:[['T001','2026-11-04','王大明','已完成','EAA-1234'],['T002','2026-11-04','陳小華','未發車','EAA-1234'],['T003','2026-11-04','林志明','執行中','KAB-5678']],'stop-times':[['T001','S001','08:00','08:00'],['T001','S002','08:12','08:13'],['T001','S003','08:35','08:35']]};
let db;try{db=JSON.parse(localStorage.getItem('bus-backstage-demo-v1'))}catch{}if(!db||!Object.keys(configs).every(k=>Array.isArray(db[k])))db=Object.fromEntries(Object.entries(seeds).map(([k,rows])=>[k,rows.map(row=>Object.fromEntries(configs[k].fields.map((f,i)=>[f[0],row[i]])))]));
// 升級舊版示範車牌，同步更新派車關聯；保留其他自訂資料。
for(const [oldPlate,newPlate] of [['BUS-001','EAA-1234'],['BUS-002','KAB-5678']]){
    if(db.buses.some(b=>b.bId===oldPlate)&&!db.buses.some(b=>b.bId===newPlate)){
        db.buses.find(b=>b.bId===oldPlate).bId=newPlate;
        db.dispatch.forEach(d=>{if(d.bId===oldPlate)d.bId=newPlate});
    }
}
// 展示用收藏關聯；正式串接時以 Favorite_Route、Favorite_Station 的資料取代。
if(!Array.isArray(db.favoriteRoutes))db.favoriteRoutes=[
    {mId:'M001',routeId:'R001'},{mId:'M002',routeId:'R001'},
    {mId:'M003',routeId:'R001'},{mId:'M004',routeId:'R001'},
    {mId:'M001',routeId:'R002'},{mId:'M003',routeId:'R002'}
];
if(!Array.isArray(db.favoriteStations))db.favoriteStations=[
    {mId:'M001',stationId:'S001'},{mId:'M002',stationId:'S001'},
    {mId:'M003',stationId:'S001'},{mId:'M004',stationId:'S001'},
    {mId:'M005',stationId:'S001'},{mId:'M001',stationId:'S002'},
    {mId:'M002',stationId:'S002'},{mId:'M003',stationId:'S002'},
    {mId:'M002',stationId:'S003'}
];
