def build_query(guild_id, game_name, min_date, max_date, user_nm=None, top_player_only=False):
    
    guild_condition = "guild_id = :guild_id"
    date_condition = "game_date BETWEEN :min_date AND :max_date"
    game_condition = "game_name = :game_name"
    user_condition = "member_nm = :user_nm"
    cols = []
    query = ""
    
    if game_name in ['winners', 'my_scores'] or min_date != max_date:
        cols = ['Game', 'Leader', 'Points', 'Wins', 'Top 3', 'Top 5', 'Played']
        user_part = f"AND {user_condition}" if game_name == 'my_scores' else ""
        top_player_part = "where z.overall_rank = 1" if top_player_only else ""
        
        query = f"""
            SELECT 
	            game_name,
                player_name,
                points,
                wins,
                ROUND(top_3 * 100) || '%' as top_3,
                ROUND(top_5 * 100) || '%' as top_5,
                participation
            FROM
                (
                SELECT
                    x.game_name,
                    dense_rank() over(partition by game_name order by points desc) as overall_rank,
                    x.player_name,
                    x.points,
                    x.wins,
                    x.top_3,
                    x.top_5,
                    max(x.games_played) over(partition by x.game_name) as total_games,
                    ROUND((x.games_played / max(x.games_played) over(partition by x.game_name)) * 100) || '%' as participation
                FROM
                    (
                    SELECT 
                        game_name,
                        player_name,
                        sum(points) as points,
                        sum(case when game_rank = 1 then 1 else 0 end) as wins,
                        sum(case when game_rank <= 3 then 1 else 0 end) / sum(1.0) as top_3,
                        sum(case when game_rank <= 5 then 1 else 0 end) / sum(1.0) as top_5,
                        sum(1) as games_played
                    FROM game_view
                    WHERE {guild_condition}
                    AND {date_condition}
                    {user_part}
                    GROUP BY 1,2
                    ) x
                ) z
            {top_player_part}
        """
        
    elif min_date == max_date:
        cols = ['Rank', 'Player', 'Score', 'Points']
        query = f"""
            SELECT 
                game_rank,
                player_name,
                game_score,
                points
            FROM game_view
            WHERE {guild_condition}
            AND {date_condition}
            AND {game_condition}
            ORDER BY game_rank;
        """
        
    return cols, query
