from pathlib import Path
from copy import deepcopy
from zipfile import ZipFile
import hashlib
from lxml import etree as E
from PIL import Image

ROOT=Path(__file__).parent
REF=Path('C:/Users/Андрей/Downloads/Корнева Д.С. лаб1.docx')
OUT=ROOT.parent/'Отчет лаб1 Общажный черный рынок.docx'
assert hashlib.sha256(REF.read_bytes()).hexdigest().upper()=='7D6BA07D8876F9C1759C862A66C29A9D78590165EA866526F61C8944B9B9E16D'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','pic':'http://schemas.openxmlformats.org/drawingml/2006/picture'}
def q(n): prefix,local=n.split(':'); return '{'+NS[prefix]+'}'+local
with ZipFile(REF) as z: parts={i.filename:z.read(i.filename) for i in z.infolist()}
doc=E.fromstring(parts['word/document.xml']); body=doc.find('w:body',NS)
paras=body.findall('w:p',NS)
rel=E.fromstring(parts['word/_rels/document.xml.rels'])
RNS='http://schemas.openxmlformats.org/package/2006/relationships'
sect=deepcopy(body.find('w:sectPr',NS))
def textpara(idx,text,break_before=False,outline=False):
    p=deepcopy(paras[idx]); pr=p.find('w:pPr',NS)
    for c in list(p):
        if c.tag!=q('w:pPr'): p.remove(c)
    r=E.SubElement(p,q('w:r')); rp=deepcopy(paras[idx].find('w:r/w:rPr',NS))
    if rp is not None:r.append(rp)
    E.SubElement(r,q('w:t')).text=text
    if break_before:E.SubElement(pr,q('w:pageBreakBefore')).set(q('w:val'),'1')
    if outline:E.SubElement(pr,q('w:outlineLvl')).set(q('w:val'),'0')
    return p
def add(idx,text,**kw): p=textpara(idx,text,**kw); body.append(p); return p
def heading(text): return add(46,text,break_before=True,outline=True)
def prose(text): return add(47,text)
def bullet(text): return add(48,text)
def sub(text):
    p=add(57,text); pr=p.find('w:pPr',NS); E.SubElement(pr,q('w:keepNext'))
    pr.find('w:spacing',NS).set(q('w:before'),'60')
    return p
def crop(name):
    im=Image.open(ROOT/(name+'.jpg')).convert('RGB')
    # Each screenshot visibly contains a 390 by 844 prototype frame at y=200.
    row=[sum(im.getpixel((x,220)))>120 for x in range(im.width)]
    groups=[]; start=None
    for x,v in enumerate(row+[False]):
        if v and start is None:start=x
        if not v and start is not None:groups.append((start,x));start=None
    left,right=min(groups,key=lambda s:abs(s[1]-s[0]-390))
    assert abs(right-left-390)<5,(name,left,right)
    result=im.crop((left,200,left+390,1044)); result.save(ROOT/(name+'.png')); return result
screens={n:crop(n) for n in ['login','register','home','details','chats','conversation','profile','add','dropdown']}
def pair(a,b,name):
    canvas=Image.new('RGB',(800,844),'white');canvas.paste(screens[a],(0,0));canvas.paste(screens[b],(410,0));canvas.save(ROOT/(name+'.png'))
pair('login','register','auth-pair');pair('chats','conversation','chat-pair');pair('add','dropdown','add-pair')
draw_src=next(p for p in paras if p.find('.//w:drawing',NS) is not None)
image_counter=0
def figure(name,number,caption,width_cm):
    global image_counter
    image_counter+=1;rid='rIdReport'+str(image_counter)
    imagepath=ROOT/(name+'.png'); im=Image.open(imagepath)
    cx=int(width_cm*360000);cy=int(cx*im.height/im.width)
    p=deepcopy(draw_src);pr=p.find('w:pPr',NS)
    for c in list(p):
        if c.tag not in [q('w:pPr'),q('w:r')]:p.remove(c)
    runs=p.findall('w:r',NS)
    kept=False
    for r in runs:
        if r.find('w:drawing',NS) is None or kept:p.remove(r)
        else:
            kept=True
            drawings=r.findall('w:drawing',NS)
            for extra in drawings[1:]:r.remove(extra)
    for t in list(pr):
        if t.tag in [q('w:ind'),q('w:spacing'),q('w:jc')]:pr.remove(t)
    E.SubElement(pr,q('w:jc')).set(q('w:val'),'center')
    sp=E.SubElement(pr,q('w:spacing'));sp.set(q('w:line'),'240');sp.set(q('w:after'),'120')
    E.SubElement(pr,q('w:keepNext'))
    for ext in p.findall('.//wp:extent',NS)+p.findall('.//a:xfrm/a:ext',NS):ext.set('cx',str(cx));ext.set('cy',str(cy))
    for blip in p.findall('.//a:blip',NS):blip.set(q('r:embed'),rid)
    for dp in p.findall('.//wp:docPr',NS):dp.set('id',str(100+image_counter));dp.set('name',name);dp.set('descr',caption)
    body.append(p)
    cap=add(121,f'Рисунок {number} – {caption}')
    sp=cap.find('w:pPr/w:spacing',NS);sp.set(q('w:line'),'240')
    media='media/report-'+name+'.png';parts['word/'+media]=imagepath.read_bytes()
    E.SubElement(rel,'{'+RNS+'}Relationship',Id=rid,Type=NS['r']+'/image',Target=media)

for c in list(body):body.remove(c)
for p in paras[:42]:body.append(deepcopy(p))
cover=body.findall('w:p',NS)
for t in cover[20].findall('.//w:t',NS):t.text='Прототип приложения «Общажный чёрный рынок»'
for t in cover[28].findall('.//w:t',NS):
    if 'группы' in t.text:t.text='Выполнил студент группы ____'
    else:t.text='ФИО'
for t in cover[32].findall('.//w:t',NS):
    if 'Проверил' not in t.text:t.text='ФИО'

add(42,'Содержание',break_before=True)
toc_entries=[('1. Цели проекта','3'),('2. Задачи проекта','4'),('3. Прототип приложения','6'),('Вывод','12')]
for i,(label,page) in enumerate(toc_entries):
    toc=textpara(47,label);pr=toc.find('w:pPr',NS)
    pr.find('w:ind',NS).set(q('w:firstLine'),'0');pr.find('w:jc',NS).set(q('w:val'),'left')
    pr.find('w:spacing',NS).set(q('w:after'),'0')
    tabs=E.SubElement(pr,q('w:tabs'));stop=E.SubElement(tabs,q('w:tab'));stop.set(q('w:val'),'right');stop.set(q('w:pos'),'9979');stop.set(q('w:leader'),'dot')
    if i==0:
        for j,(kind,value) in enumerate([('begin',None),(None,' TOC \\o "1-1" \\h \\z \\u '),('separate',None)]):
            r=E.Element(q('w:r'))
            if kind:E.SubElement(r,q('w:fldChar')).set(q('w:fldCharType'),kind)
            else:E.SubElement(r,q('w:instrText')).text=value
            toc.insert(1+j,r)
    r=E.SubElement(toc,q('w:r'));E.SubElement(r,q('w:tab'));E.SubElement(r,q('w:t')).text=page
    if i==3:
        r=E.SubElement(toc,q('w:r'));E.SubElement(r,q('w:fldChar')).set(q('w:fldCharType'),'end')
    body.append(toc)

heading('1. Цели проекта')
prose('Проект «Общажный чёрный рынок» представляет собой мобильное приложение для студентов, проживающих в общежитиях. Пользователи смогут продавать и обменивать вещи, отдавать их бесплатно, а также предлагать услуги другим студентам. Основная задача приложения — помочь найти подходящее предложение поблизости и договориться с его автором о передаче вещи или оказании услуги.')
prose('В лабораторной работе разработан интерактивный прототип в Figma. Он определяет состав экранов и основные переходы, необходимые для дальнейшей реализации мобильного клиента на React Native. Цели проекта:')
for t in [
'Объединить объявления о продаже, обмене, бесплатной передаче вещей и студенческих услугах в общей ленте.',
'Обеспечить поиск предложений по названию и категориям с учётом расположения пользователей.',
'Предоставить возможность просматривать подробности объявления и бронировать интересующую вещь.',
'Организовать общение пользователей через личные чаты для согласования условий и времени встречи.',
'Создать профиль с опубликованными объявлениями, бронированиями и переходом к добавлению нового предложения.',
'Подготовить интерфейс к работе с общей серверной базой данных, чтобы пользователи с разных устройств могли видеть одни и те же объявления и сообщения.'
]:bullet(t)
prose('Первая версия ориентирована на взаимодействие студентов друг с другом. Административная панель, жалобы и встроенная оплата не входят в рассматриваемый объём проекта.')

heading('2. Задачи проекта')
tasks=[
('2.1 Разработать экраны регистрации и авторизации',['Предусмотреть ввод имени, электронной почты и пароля, а также указание университета и общежития.','Обеспечить переходы между регистрацией, входом и главной лентой.','При реализации клиента добавить проверку введённых данных и обработку ответов сервера.']),
('2.2 Разработать главную ленту объявлений',['Отобразить карточки предложений с названием, форматом передачи и расстоянием.','Предусмотреть строку поиска и переключение категорий.','Обеспечить открытие подробной информации при нажатии на карточку.']),
('2.3 Проработать просмотр и бронирование',['Разместить изображение, описание, сведения о владельце и месте передачи.','Предусмотреть действие «Забронировать» и отображение состояния брони.','Обеспечить возврат из подробностей объявления к предыдущему экрану.']),
('2.4 Разработать форму добавления объявления',['Предусмотреть фотографии, название, описание, категорию и место передачи.','Добавить список «Формат передачи» с вариантами «Продам», «Отдам», «Услуга», «Обмен».','Связать выбор варианта с изменением значения в поле и закрытием списка.']),
('2.5 Разработать профиль пользователя',['Отобразить имя, университет и общежитие пользователя.','Разместить собственные объявления и перечень бронирований.','Добавить кнопку перехода к публикации нового предложения.']),
('2.6 Проработать чаты',['Создать экран списка переписок с названием объявления и последним сообщением.','Разработать экран диалога с карточкой объявления и разделением входящих и исходящих сообщений.','Предусмотреть поле сообщения, кнопку отправки и возврат к списку чатов.']),
('2.7 Обеспечить навигацию и согласованность интерфейса',['Использовать нижнюю панель «Главная», «Чаты», «Профиль» для основных разделов.','Связать экраны в интерактивном прототипе и предусмотреть обратные переходы.','Сохранить единое оформление карточек, полей и кнопок.']),
('2.8 Подготовить дальнейшую реализацию на React Native',['Разделить мобильный клиент, серверный API и общую базу данных.','Предусмотреть хранение аккаунтов, объявлений, фотографий, сообщений и бронирований на серверной стороне.','Обеспечить проверку прав на изменение объявлений и предотвращение одновременного бронирования одной вещи несколькими пользователями.'])]
for i,(title,items) in enumerate(tasks):
    if i==4:
        p=sub(title);E.SubElement(p.find('w:pPr',NS),q('w:pageBreakBefore')).set(q('w:val'),'1')
    else:sub(title)
    for t in items:bullet(t)

heading('3. Прототип приложения')
prose('Прототип разработан в Figma и демонстрирует интерфейс приложения и переходы между экранами. Начальный сценарий включает авторизацию или создание аккаунта. На экране регистрации предусмотрены сведения, позволяющие связать пользователя с университетом и общежитием. Экраны входа и регистрации представлены на рисунке 1.')
figure('auth-pair',1,'Экраны авторизации и регистрации',14)
prose('После нажатия кнопки входа пользователь переходит к главной ленте. Ввод данных и их проверка сервером должны быть реализованы в мобильном клиенте; прототип показывает расположение полей и навигацию.')

add(57,'Главная лента',break_before=True)
prose('Главный экран содержит строку поиска, переключатели категорий и карточки объявлений. Метки на карточках позволяют различать бесплатную передачу, обмен, продажу и услуги. В нижней части находится панель переходов к чатам и профилю (рисунок 2).')
figure('home',2,'Главный экран с объявлениями',7.6)
prose('Нажатие на карточку открывает подробности предложения. В дальнейшем поиск и фильтры будут получать объявления из общей базы данных, а расстояние будет рассчитываться на основе выбранного местоположения.')

add(57,'Подробности объявления и бронирование',break_before=True)
prose('Подробная информация представлена в виде нижнего модального окна поверх ленты. Пользователь видит изображение, формат передачи, название, описание и сведения об авторе. Кнопка «Забронировать» запускает сценарий договорённости о получении вещи (рисунок 3).')
figure('details',3,'Модальное окно объявления',7.6)
prose('Бронирование обозначает намерение получить вещь и не является оплатой. При реализации приложения сервер должен проверять доступность предложения и сохранять бронь. Условия обмена, продажи или услуги пользователи уточняют в переписке.')

add(57,'Чаты и переписка',break_before=True)
prose('В разделе «Чаты» представлены переписки по объявлениям. Карточка диалога содержит название предложения, собеседника и последнее сообщение; для непрочитанных сообщений предусмотрен счётчик. Экран переписки показывает связанное объявление, историю сообщений и поле для ответа (рисунок 4).')
figure('chat-pair',4,'Список чатов и экран переписки',14)
prose('Входящие и исходящие сообщения различаются расположением и фоном. Через чат студенты согласовывают время и место передачи вещи. Сохранение и синхронизация сообщений между устройствами относятся к дальнейшей серверной реализации.')

add(57,'Профиль пользователя',break_before=True)
prose('Профиль объединяет сведения о пользователе, его объявления и бронирования. У опубликованных вещей отображается состояние, например «Опубликовано» или «Забронировано». Кнопка с символом «+» открывает форму добавления объявления (рисунок 5).')
figure('profile',5,'Профиль и собственные объявления',7.6)
prose('Раздел «Ваши бронирования» позволяет вернуться к интересующим предложениям. Нижняя панель сохраняет доступ к главной ленте и чатам без повторного прохождения авторизации.')

add(57,'Добавление объявления и формат передачи',break_before=True)
prose('Форма добавления содержит область фотографий, название, описание, категорию, формат передачи и место. В поле «Формат передачи» реализован интерактивный список из четырёх вариантов: «Продам», «Отдам», «Услуга», «Обмен». Закрытое и раскрытое состояния показаны на рисунке 6.')
figure('add-pair',6,'Форма публикации и список форматов передачи',14)
prose('Нажатие на поле открывает список над ним. Выбор варианта изменяет значение в поле и закрывает меню. При повторном открытии текущий вариант выделен. Кнопка «Опубликовать» завершает сценарий заполнения формы; фактическое сохранение объявления будет выполняться через серверный API.')

heading('Вывод')
prose('В ходе лабораторной работы разработан интерактивный прототип мобильного приложения «Общажный чёрный рынок» для продажи, обмена и бесплатной передачи вещей, а также размещения студенческих услуг. Определены цели и задачи проекта, подготовлены экраны авторизации, регистрации, ленты, подробностей объявления, чатов, профиля и добавления вещи.')
prose('В прототипе предусмотрены переходы между основными разделами и обратная навигация. Для формы публикации создан список форматов передачи с четырьмя вариантами и изменением выбранного значения. Макет служит основой для реализации мобильного клиента на React Native.')
prose('Планируется клиент-серверная архитектура: приложение на смартфоне обращается к серверному API, а пользователи, объявления, сообщения и бронирования хранятся в общей базе данных на сервере. Благодаря этому установленный на разных устройствах клиент сможет работать с едиными данными. На этапе данной лабораторной работы создан прототип интерфейса; серверная часть и база данных ещё не реализованы.')
prose('Прототип проекта доступен по ссылке:')
p=add(47,'https://www.figma.com/design/Il1x1YL5rRDL3cPNb2tquG/');p.find('w:pPr/w:ind',NS).set(q('w:firstLine'),'0')
body.append(sect)
parts['word/document.xml']=E.tostring(doc,xml_declaration=True,encoding='UTF-8',standalone=True)
parts['word/_rels/document.xml.rels']=E.tostring(rel,xml_declaration=True,encoding='UTF-8',standalone=True)
core=E.fromstring(parts['docProps/core.xml'])
for n in core:
    if E.QName(n).localname in ['creator','lastModifiedBy']:n.text=''
parts['docProps/core.xml']=E.tostring(core,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(OUT,'w') as z:
    for name,data in parts.items():z.writestr(name,data)
changed=[]
with ZipFile(REF) as z:
    for n in z.namelist():
        if parts[n]!=z.read(n):changed.append(n)
assert set(changed)<= {'word/document.xml','word/_rels/document.xml.rels','docProps/core.xml'}
print(OUT);print('Changed original parts:',changed)
