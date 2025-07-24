import streamlit as st
import streamlit.components.v1 as components

from pyvis.network import Network
from db.neo4j_connector import Neo4jConnection

from dotenv import load_dotenv
import os

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PWD = os.getenv("NEO4J_PWD")

conn = Neo4jConnection(uri=NEO4J_URI, user=NEO4J_USER, pwd=NEO4J_PWD)

# streamlit setting
st.set_page_config(layout="wide")
st.title("Honeyz 음악 저장고")
menu = st.sidebar.radio(
    "메뉴 선택",
    ("그래프", "테이블", "통계")
)

if menu == "그래프":
    st.header("그래프")

    # member list selection
    members = [record['name'] for record in conn.query(
        "MATCH (m:Member) RETURN m.name AS name ORDER BY name"
    )]
    all_label="전체"
    member_options = [all_label] + members

    selected_members = st.multiselect("멤버 선택", member_options, default=[all_label])

    # Query
    if all_label in selected_members or not selected_members:
        active_members = members
    else:
        active_members = selected_members

    if active_members:
        # perf_title 기준으로 그룹화, 관련 Performance와 Song의 링크/날짜/타입을 모두 모음
        query = '''
        MATCH (m:Member)<-[:PERFORMED_BY]-(p:Performance)-[:COVERS]->(s:Song)-[:HAS_GENRE]->(g:Genre)
        WHERE m.name IN $members
        RETURN 
            m.name AS member, id(m) AS member_id,
            p.title AS perf_title, COLLECT(DISTINCT id(p)) AS perf_ids, COLLECT(DISTINCT p.clip_link) AS perf_links, p.type AS type, p.data AS date,
            s.title AS song, id(s) AS song_id,
            g.type AS genre_type, g.name AS genre_name, id(g) AS genre_id
        '''
        records = conn.query(query, parameters={"members": active_members})
    else:
        records = []

    FONT_SIZE = 64
    added_members, added_perfs, added_songs, added_genres = set(), set(), set(), set()

    net = Network(height="700px", width="100%", directed=False)
    net.barnes_hut()
    
    from collections import defaultdict

    # 1. Song별 모든 Performance의 링크 수집
    song_links_dict = defaultdict(set)
    for rec in records:
        s_id = rec['song_id']
        links = rec['perf_links'] if isinstance(rec['perf_links'], list) else [rec['perf_links']]
        titles = rec['perf_title'] if isinstance(rec['perf_title'], list) else [rec['perf_title']]
        for link, title in zip(links, titles):
            if link and link.strip():
                song_links_dict[s_id].add((link, title))

    for rec in records:
        m_id, member = rec['member_id'], rec['member']
        perf_title = rec['perf_title']
        perf_key = perf_title  # Performance 노드를 perf_title로 그룹핑
        perf_links = rec['perf_links'] if isinstance(rec['perf_links'], list) else [rec['perf_links']]
        perf_type = rec['type']
        date = rec['date']
        s_id, song = rec['song_id'], rec['song']
        g_id, genre_type, genre_name = rec['genre_id'], rec['genre_type'], rec['genre_name']
        genre_label = f"{genre_type}/{genre_name}"

        # Member 노드
        if m_id not in added_members:
            net.add_node(
                m_id, label=member,
                color="#ffcc00", shape="circle",
                font={'size': FONT_SIZE, 'color': 'black', 'face': 'Noto sans'}
            )
            added_members.add(m_id)

        # Performance 노드 (perf_title로 그룹화, 여러 perf_id/회차를 하나로)
        if perf_key not in added_perfs:
            perf_type_text = ", ".join(perf_type) if isinstance(perf_type, list) else perf_type
            perf_html = f"""
            <div style='background:#fff;border-radius:18px;box-shadow:0 2px 16px 0 #0002;padding:17px 20px 13px 20px;min-width:280px;max-width:340px;font-family:Malgun Gothic,sans-serif;'>
            <div style='font-size:16px;font-weight:700;color:#222;margin-bottom:4px;'>🎤 {perf_title}</div>
            <div style='color:#222;font-size:14px;margin-bottom:4px;'><b>날짜:</b> {date}</div>
            <div style='margin-bottom:4px;'><b>타입:</b> <span style='background:#e3fcec;color:#2b9348;border-radius:6px;padding:2px 8px;font-size:12px;'>{perf_type_text}</span></div>
            </div>
            """
            net.add_node(
                perf_key, label=perf_title, color="#eabfff", shape="diamond",
                font={'size': FONT_SIZE, 'color': '#7b27c5', 'face': 'Malgun Gothic'},
                title=perf_html
            )
            added_perfs.add(perf_key)

        # Song 노드 (여러 영상 링크를 버튼으로 노출)
        if s_id not in added_songs:
            # Performance에 여러 회차가 있다면 여러 영상 버튼으로 info panel 생성
            video_buttons = ""
            for link, title in song_links_dict[s_id]:
                video_buttons += f"""
                    <a href='{link}' target='_blank' style='
                        background:#222;color:#fff;border-radius:8px;
                        padding:7px 20px;font-size:13px;font-weight:500;
                        text-decoration:none;display:inline-block;margin:4px 0 4px 0;'>
                        🎬 {title}
                    </a><br>
                """
            song_html = f"""
            <div style='font-family:Malgun Gothic,sans-serif;'>
                <div style='background:#fff;border-radius:18px;box-shadow:0 2px 16px 0 #0002;padding:17px 20px 13px 20px;min-width:280px;max-width:340px;font-family:Malgun Gothic,sans-serif;'>
                <div style='font-size:16px;font-weight:700;color:#222;margin-bottom:4px;'>🎤 {song}</div>
                {video_buttons}
                </div>
            </div>
            """
            net.add_node(
                s_id, label=song,
                color="#66b3ff", shape="box",
                font={'size': FONT_SIZE, 'color': 'black', 'face': 'Malgun Gothic'},
                title=song_html
            )
            added_songs.add(s_id)

        # Genre 노드
        if g_id not in added_genres:
            net.add_node(
                g_id, label=genre_label,
                color="#ccffcc", shape="hexagon",
                font={'size': FONT_SIZE, 'color': '#265c27', 'face': 'Malgun Gothic'}
            )
            added_genres.add(g_id)

        # 관계(Edge)들
        net.add_edge(m_id, perf_key, color="#ffcc00", width=2)        # 멤버-Performance
        net.add_edge(perf_key, s_id, color="#aabaff", width=2)        # Performance-곡
        net.add_edge(s_id, g_id, color="#77dd77", width=2)            # 곡-장르

    net.save_graph("pyvis_graph.html")
    with open("pyvis_graph.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=1080)

elif menu == "테이블":
    st.header("테이블")
    
    
    
    is_songbook = st.toggle("노래책 모드", value=False)
    
    if is_songbook:
        query = """
        MATCH (m:Member)<-[:PERFORMED_BY]-(p:Performance)-[:COVERS]->(s:Song)-[:ORIGINAL_BY]->(a:Artist),
        (s)-[:HAS_GENRE]->(g:Genre)
        RETURN
        s.title AS song,
        a.name AS artist,
        COLLECT(DISTINCT m.name) AS members,
        COLLECT(DISTINCT g.type + '/' + g.name) AS genres,
        s.lyrics_url AS lyrics_url
        ORDER BY s.title, artist
        """
        records = conn.query(query)
        
        songbook_data = []
        for idx, rec in enumerate(records, start=1):
            members = ", ".join(sorted(rec['members']))
            genres = ", ".join(sorted(rec['genres']))
            songbook_data.append({
                "번호": idx,
                "노래": rec['song'],
                "원곡자": rec['artist'],
                "장르": genres,
                "멤버": members,
                "가사": f"{rec['lyrics_url']}" if rec['lyrics_url'] else ""
            })
        import pandas as pd
        df = pd.DataFrame(songbook_data)
        
        st.dataframe(df,
                    column_config={
                        "가사": st.column_config.LinkColumn(),
                        "번호": st.column_config.Column(width='small')
                    },
                    hide_index=True
        )
    else:
        members = [r['name'] for r in conn.query("MATCH (m:Member) RETURN m.name AS name ORDER BY name")]
        genres = [f"{r['type']}/{r['name']}" for r in conn.query("MATCH (g:Genre) RETURN g.type AS type, g.name AS name ORDER BY g.type, g.name")]

        selected_member = st.selectbox("멤버 선택", ["전체"] + members)
        selected_genre = st.selectbox("장르 선택", ["전체"] + genres)
        where_clause = []
        params = {}
        if selected_member != "전체":
            where_clause.append("m.name = $member")
            params['member'] = selected_member
        if selected_genre != "전체":
            genre_type, genre_name = selected_genre.split("/", 1)
            where_clause.append("g.type = $genre_type AND g.name = $genre_name")
            params.update({"genre_type": genre_type, "genre_name": genre_name})
            
        where_cypher = "WHERE " + " AND ".join(where_clause) if where_clause else ""
        query = f"""
        MATCH (m:Member)<-[:PERFORMED_BY]-(p:Performance)-[:COVERS]->(s:Song)-[:HAS_GENRE]->(g:Genre)
        {where_cypher}
        RETURN 
        id(p) AS perf_id,
        COLLECT(DISTINCT m.name) AS members,
        s.title AS song,
        COLLECT(DISTINCT g.type + '/' + g.name) AS genres,
        p.type AS type,
        p.data AS date,
        p.clip_link AS clip_link
        ORDER BY p.data DESC
        """
        records = conn.query(query, parameters=params)
        
        # 테이블 생성
        import pandas as pd
        
        table_data = []
        for rec in records:
            members = ", ".join(rec['members'])
            genres = ", ".join(rec['genres'])
            perf_type = ", ".join(rec['type']) if isinstance(rec['type'], list) else str(rec['type'])
            table_data.append({
                "멤버": members,
                "노래": rec['song'],
                "장르": genres,
                "타입": perf_type,
                "날짜": rec['date'],
                "영상 링크": rec['clip_link']
            })
        df = pd.DataFrame(table_data)
        
        st.dataframe(df,
                    column_config={
                        "영상 링크": st.column_config.LinkColumn()
                    },
                    hide_index=True
        )
    
elif menu == "통계":
    import pandas as pd
    import plotly.express as px
    import math
    st.header("통계")
    
    tab1, tab2, tab3 = st.tabs(["월별 부른 곡 추이", "연도별 부른 곡 추이", "장르 히트맵"])
    
    with tab1:
        # 월별 부른 곡 추이
        st.subheader("월별 부른 곡 추이")
        
        # member list selection
        members = [record['name'] for record in conn.query(
            "MATCH (m:Member) RETURN m.name AS name ORDER BY name"
        )]
        all_label="전체"
        member_options = [all_label] + members

        selected_members = st.multiselect("멤버 선택", member_options, default=[all_label])

        # Query
        if all_label in selected_members or not selected_members:
            active_members = members
        else:
            active_members = selected_members
            
        query_month = """
        MATCH (p:Performance)-[r:PERFORMED_BY]->(m:Member)
        WHERE p.data IS NOT NULL AND m.name IN $members
        WITH date(p.data) AS dt, p
        RETURN dt.year AS year, dt.month AS month, COUNT(p) AS perf_count
        ORDER BY year, month
        """
        records_month = conn.query(query_month, parameters={"members": active_members})
        month_data = []
        for rec in records_month:
            month_data.append({
                "year": rec['year'],
                "month": rec['month'],
                "perf_count": rec['perf_count']
            })
        df_month = pd.DataFrame(month_data)
        df_month["연월"] = df_month["year"].astype(str) + "-" + df_month["month"].astype(str).str.zfill(2)
        
        fig_month = px.line(
            df_month,
            x="연월",
            y="perf_count",
            markers=True,
            labels={"연월": "연-월", "perf_count": "부른 곡 수"},
            title="월별 부른 곡 수 추이"
        )
        fig_month.update_traces(line=dict(width=3))
        st.plotly_chart(fig_month, use_container_width=True)
    
    with tab3:
        # 장르 히트맵
        st.subheader("장르 히트맵")
        
        query = """
        MATCH (m:Member)<-[:PERFORMED_BY]-(p:Performance)-[:COVERS]->(s:Song)-[:HAS_GENRE]->(g:Genre)
        RETURN 
            m.name AS member,
            g.type AS main_genre,
            g.name AS sub_genre,
            COUNT(DISTINCT p) AS perf_count
        """
        records = conn.query(query)
        records_data = []
        for rec in records:
            records_data.append({
                "member": rec['member'],
                "main_genre": rec['main_genre'],
                "sub_genre": rec['sub_genre'],
                "perf_count": rec['perf_count']
            })
        
        df = pd.DataFrame(records_data)
        member_list = sorted(df["member"].unique())
        main_genres = sorted(df["main_genre"].unique())
        sub_genres = sorted(df["sub_genre"].unique())
        
        n_col = 2
        n_row = math.ceil(len(member_list) / n_col)

        # 멤버를 2명씩 슬라이싱해서 각 열에 배치
        member_groups = [member_list[i*n_row:(i+1)*n_row] for i in range(n_col)]
        cols = st.columns(n_col)
        k = 1
        for members, col in zip(member_groups, cols):
            with col:
                for i, member in enumerate(members):
                    st.markdown(f"##### {member}")
                    df_mem = df[df["member"] == member]
                    df_pivot = df_mem.pivot(index="sub_genre", columns="main_genre", values="perf_count").fillna(0).astype(int)
                    fig = px.imshow(
                        df_pivot,
                        text_auto=True,
                        color_continuous_scale="Blues",
                        aspect="auto",
                        labels=dict(x="국가(지역)", y="세부장르", color="곡 수")
                    )
                    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=350)
                    st.plotly_chart(fig, use_container_width=True, key=f"plot_heatmap_{(i+1) + k}")
            k += 3

import atexit
atexit.register(lambda: conn.close())