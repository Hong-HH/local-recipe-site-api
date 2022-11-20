
# recipe list request type 에 대한 query 문 매칭




def recipe_list_map (list_type, params) :

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
                                on r.user_id = u.id ''',


                        "created_at_query_start" : '''  select rr.* , u.nickname, u.profile_img, u.profile_desc
                                                        from 
                                                        (select r.* , count(uh.id) as views
                                                        from 
                                                        (select rc.* ,  count(l.created_at) as like_cnt
                                                        from 
                                                        (select *
                                                        from recipe
                                                        where recipe.public = 1 ''',
                        "created_at_query_end" : ''' order by id desc
                                                        limit 10) as rc
                                                        left join likes as l
                                                        on rc.id = l.recipe_id 
                                                        group by rc.id) as r
                                                        left join user_history as uh
                                                        on r.id = uh.recipe_id
                                                        group by r.id) as rr

                                                        left join user as u
                                                        on rr.user_id = u.id; ''',
                        
                        "best_query_start" : ''' select r.*, u.nickname, u.profile_img, u.profile_desc
                                                from 
                                                (select rl.*, count(uh.created_at) as views
                                                from 
                                                (select rn.*, count(l.created_at) as likes_cnt
                                                from recipe rn
                                                left join likes l
                                                on rn.id = l.recipe_id
                                                group by recipe_id
                                                having public = 1  ''',
                        "best_query_end" : '''  limit 2  
                                                order by likes_cnt desc) as rl
                                                left join user_history as uh
                                                on rl.id = uh.recipe_id
                                                group by recipe_id) as r
                                                left join user as u
                                                on r.user_id = u.id; '''


                        }

    if list_type == "best" :
        query =  list_type_map[list_type]
        query = query + ''' where public = 1
                            limit 10;'''
        return query
    elif list_type == "classification"  :
        # text = "면류,술안주,해물류"
        # text_list = text.split(",")
        # ['면류', '술안주', '해물류']
        # ['전체' , '전체', '전체']
        
        text = params["category"]
        text_list = text.split(",")
        if params["order_by"] == "like" :
            query =  list_type_map["best"]

            # 카테고리의 unique 값이 하나라면 3개의 카테고리 모두 전체이다.
            if len(set(text_list)) == 1 :
                query = query + ''' where public = 1 '''

            else :
                category_list = ['category_type','category_context','category_ingredients']
                subquery_name_list = ['c1', 'c2' , 'c3']
                after_query = ''' where public = 1 '''   

                i = 0
                for t in text_list:
                    if t == "전체" :
                        pass
                    else :
                        query = query + '''left join
                                            (SELECT id FROM category 
                                            where  FIELD(name, \"''' + t + '''\"  ) ) as '''+ subquery_name_list[i] + '''
                                            on ''' + category_list[i] +''' = '''+ subquery_name_list[i]  + '''.id'''

                        after_query = after_query + ''' and not ''' + subquery_name_list[i] + '''.id is null '''
                    i = i + 1


            if "target_id" in params:
                query = query + " and id < " + params["target_id"] +  after_query     +  " limit 15;"
                print (query)
                return query
            else :
                query = query + after_query  +  " limit 15;"
                print (query)
                return query

    elif list_type == "search"  :
        pass



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
                                        (%s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s);''',

                        "get_ingredient_id" : '''select * from ingredient
                                                    where name = %s;''',
                            
                        "get_bundle_id" : '''insert into
                                            ingredient_bundle
                                            (name)
                                            values
                                            (%s);''',

                        "insert_get_ingredient_id" : '''insert into ingredient
                                                            (name)
                                                            values
                                                            (%s);''',

                        "insert_recipe_ingredient" : '''insert into recipe_ingredient
                                                        (recipe_id, ingredient_id, amount, bundle_id)
                                                        values
                                                        (%s, %s, %s, %s);'''




}
    # return recipe_detail_query[keyword]