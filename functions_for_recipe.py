
# recipe list request type 에 대한 query 문 매칭




def recipe_list_map (list_type) :


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


# def recipe_detail_query_map (keyword) : 
recipe_detail_query = {
                        "recipe_user_info" : '''
                                            select r.id, r.user_id, u.nickname, u.profile_img, u.profile_desc, r.header_title as title, 
                                            r.header_img as mainSrc, r.header_desc as intro, r.result_img,
                                            r.created_at, r.updated_at,  c1.name as c_type, c2.name as c_ctx , c3.name as c_ind, 
                                            c4.name as c_s, c5.name as c_time,c6.name as c_level
                                            from 
                                            (select *
                                            from recipe
                                            where id = %s ) as r
                                            left join
                                            category as c1
                                            on r.category_type = c1.id
                                            left join
                                            category as c2
                                            on r.category_context = c2.id
                                            left join
                                            category as c3
                                            on r.category_ingredients = c3.id
                                            left join
                                            category as c4
                                            on r.servings = c4.id
                                            left join
                                            category as c5
                                            on r.time = c5.id
                                            left join
                                            category as c6
                                            on r.level = c6.id 
                                            left join
                                            (select un.id, un.nickname, un.profile_img , profile_desc
                                            from user as un) as u
                                            on r.user_id = u.id;
                                            ''',

                        "recipe_ingredient" : '''select ifnull(ib.name, '재료')  as bundle ,i.name, ri.amount
                                                from (select *
                                                from recipe_ingredient
                                                where recipe_id = %s) as ri
                                                left join ingredient as i
                                                on ri.ingredient_id = i.id
                                                left join ingredient_bundle as ib
                                                on ri.bundle_id = ib.id
                                                order by bundle;''',

                        "step" : '''select step, description, img
                                    from recipe_step
                                    where recipe_id = %s
                                    order by step;''',

                        "like_view" : '''select v.views, l.like_cnt
                                            from 
                                            (select ifnull(recipe_id, %s) as recipe_id, count(*) as views
                                            from user_history
                                            where recipe_id = %s) as v
                                            join
                                            (select  ifnull(recipe_id, %s) as recipe_id ,  count(*) as like_cnt
                                            from likes
                                            where recipe_id = %s) as l
                                            using (recipe_id);''',

                        "is_liked" : '''select *
                                        from likes
                                        where recipe_id = 3 and user_id = 13;''',

                        "add_view" : '''insert into user_history
                                        (user_id,recipe_id)
                                        values
                                        (%s, %s);''',

                        "get_user_id" : '''select id, external_id
                                            from user
                                            where external_id = %s;''',

                        "get_category_id" : '''select * from category
                                                where name in (%s, %s, %s, %s, %s, %s )
                                                order by id;''',


                        "add_recipe" : '''insert into recipe
                                        (user_id,public, category_type, category_context, category_ingredients, header_img, header_title, header_desc, servings, time, level, result_img)
                                        values
                                        (%s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s);'''




}
    # return recipe_detail_query[keyword]