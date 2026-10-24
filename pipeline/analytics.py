        threshold_rows AS (
            SELECT
                ev.video_id,
                ev.published_at,
                rs.fetched_on,
        
                ROW_NUMBER() OVER (
                    PARTITION BY ev.video_id
                    ORDER BY rs.fetched_on ASC, rs.snapshot_id ASC
                ) AS threshold_rank
        
            FROM eligible_videos ev
            JOIN ranked_snapshots rs
                ON ev.video_id = rs.video_id
            JOIN latest_views lv
                ON ev.video_id = lv.video_id
        
            WHERE rs.views >= 0.80 * lv.latest_views
        ),
        
        shelf_life AS (
            SELECT
                video_id,
                fetched_on::date - published_at::date AS shelf_life_days
            FROM threshold_rows
            WHERE threshold_rank = 1
        ),
        
        categorised AS (
            SELECT
                video_id,
                shelf_life_days,
        
                CASE
                    WHEN shelf_life_days <= 1
                        THEN 'Within 24 hours'
                    WHEN shelf_life_days <= 3
                        THEN '2–3 days'
                    WHEN shelf_life_days <= 7
                        THEN '4–7 days'
                    ELSE '7+ days'
                END AS shelf_life_category,
        
                CASE
                    WHEN shelf_life_days <= 1 THEN 1
                    WHEN shelf_life_days <= 3 THEN 2
                    WHEN shelf_life_days <= 7 THEN 3
                    ELSE 4
                END AS category_order
        
            FROM shelf_life
        )
        
        SELECT
            shelf_life_category,
            COUNT(*) AS video_count,
            ROUND(
                100.0 * COUNT(*) /
                SUM(COUNT(*)) OVER (),
                2
            ) AS percentage
        
        FROM categorised
        GROUP BY shelf_life_category, category_order
        ORDER BY category_order;
    """)
    df["shelf_life_category"] = df["shelf_life_category"].str.upper()
    print("Shelf-life query completed.")
    print("Rows returned:", len(df))
    print(df.head())
    push(sh, "shelf_life", df)
    print("Shelf-life data pushed to Google Sheets.")

    conn.close()
    print(f"✓ analytics.py completed at {datetime.now().strftime('%d %b %Y, %I:%M %p')}")


def run_backup():
    """Copy charts_engage → yesterday_analytics. Run manually after visual check."""
    gc     = get_gspread()
    source = gc.open("charts_engage")
    backup = gc.open("yesterday_analytics")

    tabs = [
        "subscribers", "total_views", "Top_5_videos",
        "videos_per_day", "posting_time_of_videos", "duration_of_videos",
        "engagement_score", "vph_vs_volume", "eng_scr_vs_vol",
        "editorial_effort_web", "editorial_effort_tv", "editorial_effort_print", "views_by_duration_channel", "views_by_duration_segment, short_quant"
    ]

    for tab in tabs:
        data = source.worksheet(tab).get_all_values()
        ws   = backup.worksheet(tab)
        ws.clear()
        ws.update(data)
        print(f"✓ {tab}")
        time.sleep(3)

    print("\nBackup complete.")


if __name__ == "__main__":
    run_analytics()
