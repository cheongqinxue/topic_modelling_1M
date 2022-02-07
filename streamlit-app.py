import streamlit as st
import streamlit_wordcloud as wordcloud
import json
import pandas as pd
from rapidfuzz import process, fuzz
import plotly.graph_objects as go
st.set_page_config(layout="wide")
import s3fs
FS = s3fs.S3FileSystem(anon=False)
# import codecs as FS

@st.cache
def load(file):
    with FS.open(file) as f:
        data = json.loads(f.read())
        
    df = pd.DataFrame(data)
    df['representative_title'] = df['titles'].apply(lambda x: x[0])
    df = df.set_index('topic', drop=False)

    words = list(set([kw for w in df.keywords.tolist() for kw in w]))

    wordindex = []

    for w in words:
        subdf = df.keywords.map(set([w]).issubset)
        subdf = df[subdf]
        wordindex.append({
            'keyword':w,
            'topics':subdf.topic.tolist()})

    wordindex = pd.DataFrame(wordindex)

    return df, wordindex

def renderdf(row, container):
    fig = go.Figure(
            data=[
                go.Table(
                    columnwidth=[1,9],
                    header=dict(values=['Topic Number','Representative Title'],
                        fill_color='lightsteelblue',
                        font_color='black',
                        font_size=15,
                        align='left'),
                    cells=dict(values=[row.topic, row.representative_title],
                        fill_color='#EEEEEE',
                        font_size=13,
                        align='left')
                )
            ])
    fig.update_layout(
        margin=dict(l=20, r=20, t=5, b=5),height=250)
    container.plotly_chart(fig, use_container_width=True)

def main():
    df_, index_df = load(st.secrets['TOPIC_URL'])
    # df_, index_df = load('processed.json')
    df = df_.copy(deep=True)
    gettopic = st.sidebar.text_input(label='Enter a topic number to view')
    searchword = st.sidebar.text_input(label='Enter a keyword to search')
    if searchword != '':
        res = process.extract(searchword, index_df.keyword.tolist(), scorer=fuzz.WRatio, limit=10)
        _,_,res = zip(*res)
        res = index_df.iloc[list(res),:]['topics'].tolist()
        res = [t for r in res for t in r]
        res = [{'Topic number':t,'Sample Title':df.loc[t].representative_title} for t in res]
        st.sidebar.write(res)

    if gettopic != '' and gettopic.isnumeric():
        gettopic = int(gettopic)
        if gettopic not in df.topic:
            st.write(f'{gettopic} is not valid')
        else:
            x = df.loc[gettopic]
            st.caption('Representative Title')
            st.markdown(f'#### {x.representative_title}')
            words = [{'text':w, 'value':s} for w, s in zip(x['keywords'], x['kwscores'])]
            return_obj = wordcloud.visualize(words, per_word_coloring=False, enable_tooltip=False, 
                layout='archimedean', width='50%', font_min=30, font_max=60)
            st.caption('All members of the topic')
            # st.dataframe({'Titles':x['all_titles'],'Truncated Content':x['all_trunc_content']}, height=500, width=400)
            for title, content in zip(x['titles'], x['contents']):
                with st.expander(title):
                    st.write(content)
            st.caption('Non-member neighbors of the topic')
            for title, content in zip(x['nb_title'], x['nb_content']):
                with st.expander(title):
                    st.write(content)
            
            

    st.caption('All Topics List')
    renderdf(df, st)

if __name__=='__main__':
    main()
