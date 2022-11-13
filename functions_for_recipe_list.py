
# recipe list request type 에 대한 query 문 매칭

def recipe_list_map () :

    list_type = "best"

    list_type_map = {
                    "best" :'''select r.id as recipe_id ,l_b_v.likes_cnt , l_b_v.views , r.user_id, u.nickname, u.profile_img , r.public, r.header_img, r.header_title, r.created_at
                    from 
                    (select l_b.recipe_id, l_b.likes_cnt , count(*) as views
                    from 
                    (SELECT recipe_id , count(*) as likes_cnt
                    FROM likes
                    group by recipe_id
                    order by likes_cnt desc
                    limit 0, 10) as l_b

                    left join user_history as uh
                    on l_b.recipe_id = uh.recipe_id
                    group by l_b.recipe_id) as l_b_v

                    left join recipe as r
                    on l_b_v.recipe_id = r.id

                    left join
                    (select un.id, un.nickname, un.profile_img
                    from user as un) as u
                    on r.user_id = u.id;'''


                        }

    return list_type_map[list_type]