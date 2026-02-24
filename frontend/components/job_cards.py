import streamlit as st
from services.jobs_service import dateparse


def render_job_cards(cards: list[dict]):
    if not cards:
        st.info("조회된 채용공고가 없습니다.")
        return

    for card in cards:
        with st.container(border=True):
            a, b = st.columns([8, 2])
            
            with a:
                logo = card.get("logo")

                if logo:
                    st.image(logo, width=120)

                st.markdown(
                    f"<p style='font-size:16px; font-weight:700; margin-bottom:4px; color:#111;'>{card['company']} — {card['title']}</p>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<p style='font-size:14px; color:#666; margin:0;'>{card.get('co_type', '') or ''}</p>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<p style='font-size:14px; color:#666; margin:0;'>{card.get('emp_type', '') or ''}</p>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<p style='font-size:14px; color:#666; margin:0; padding-bottom:12px;'>{dateparse(card.get('start_dt'))} ~ {dateparse(card.get('end_dt'))}</p>",
                    unsafe_allow_html=True
                )

            with b:
                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                st.link_button(
                    "지원하기",
                    url=card["link"],
                    use_container_width=True
                )