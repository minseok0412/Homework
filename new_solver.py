import os.path
from prob_builder import *
from typing import List
import pickle
PENALTY = 1000000

# 재혁
def rule_solver(instance: Prob_Instance) -> dict:
    print('Solver Start')
    solution = {}
    solution['Problem'] = instance.deepcopy()

    req_list = instance.req_list
    req: Request
    for req in req_list:
        req.initialize()

    stn_list = instance.stn_list
    stn: Station
    for stn in stn_list:
        stn.initialize()

    if not os.path.exists('dist.p'):
        distance_dic = {}

        for req in req_list:
            for st in stn_list:
                distance_dic[dic_key(req.loc, st.loc)] = get_distance_lat(req.loc, st.loc)
                distance_dic[dic_key(st.loc, req.loc)] = get_distance_lat(st.loc, req.loc)

        for req1 in req_list:
            for req2 in req_list:
                if req1.id != req2.id:
                    distance_dic[dic_key(req1.loc, req2.loc)] = get_distance_lat(req1.loc, req2.loc)
                    distance_dic[dic_key(req2.loc, req1.loc)] = get_distance_lat(req2.loc, req1.loc)


        with open('dist.p', 'wb') as file:
            pickle.dump(distance_dic, file)

    else:
        with open('dist.p', 'rb') as file:
            distance_dic = pickle.load(file)

        for req in req_list:
            for st in stn_list:
                if dic_key(req.loc, st.loc) not in distance_dic:
                    distance_dic[dic_key(req.loc, st.loc)] = get_distance_lat(req.loc, st.loc)
                    distance_dic[dic_key(st.loc, req.loc)] = get_distance_lat(st.loc, req.loc)

        for req1 in req_list:
            for req2 in req_list:
                if req1.id != req2.id and (dic_key(req1.loc, req2.loc) not in distance_dic):
                    distance_dic[dic_key(req1.loc, req2.loc)] = get_distance_lat(req1.loc, req2.loc)
                    distance_dic[dic_key(req2.loc, req1.loc)] = get_distance_lat(req2.loc, req1.loc)

        with open('dist.p', 'wb') as file:
            pickle.dump(distance_dic, file)




    def priority(target, station_list: List[Station]):
        not_move_station = list(filter(lambda x: isinstance(x, MovableStation) is False, station_list))
        move_station = list(filter(lambda x: isinstance(x, MovableStation) is True, station_list))
        pri_dic = {}

        for stn in not_move_station:
            if stn.doable(target):
                try:
                    dist = distance_dic[dic_key(target.loc, stn.loc)] # 위의 딕셔너리에서 값 바로 가져오기
                except Exception:
                    dist = (get_distance_lat(target.loc, stn.loc)) # 위의 딕셔너리에서 값 바로 가져오기
                # wait_time = abs(min(0,target.start_time + dist / 60 - stn.measures['total_time']))
                start_time = max(stn.measures['total_time'],(target.start_time + dist / 60))
                tardiness_time = max(0,(start_time + (target.rchg_amount / stn.rchg_speed) - target.time_wdw[1]))
                pri_dic[tardiness_time] = [target, stn, dist]
                target.dist_list.append(tardiness_time)



        if 0 not in target.dist_list:
            for stn in move_station:
                if stn.doable(target):
                    try:
                        dist = distance_dic[dic_key(stn.loc, target.loc)]  # 위의 딕셔너리에서 값 바로 가져오기
                    except Exception:
                        dist = (get_distance_lat(stn.loc, target.loc))  # 위의 딕셔너리에서 값 바로 가져오기

                    try:
                        origin_dist = distance_dic[dic_key(stn.start_loc, target.loc)]  # 위의 딕셔너리에서 값 바로 가져오기
                    except Exception:
                        origin_dist = (get_distance_lat(stn.start_loc, target.loc))  # 위의 딕셔너리에서 값 바로 가져오기
                    # wait_time = abs(min(0, target.start_time - stn.measures['total_time']))
                    if origin_dist < 50:  # m_stn의 초기 위치에서 벗어나지 않는다면 실행. 2km 이내
                        start_time = max(stn.measures['total_time'], target.start_time) + dist / stn.move_speed
                        tardiness_time = max(0, (start_time + (target.rchg_amount / stn.rchg_speed) - target.time_wdw[1]))
                        pri_dic[tardiness_time] = [target, stn, dist]
                        target.dist_list.append(tardiness_time)


        # pri_time = sorted(pri_dic.keys(), key=lambda x :(x, pri_dic[x][2]))
        pri_time = sorted(pri_dic.keys(),key = lambda x:(x,pri_dic[x][2]))

        return pri_dic[pri_time[0]][0], pri_dic[pri_time[0]][1]
    # ==================================================================
    for req in req_list:
        for stn in stn_list:
            if isinstance(stn, MovableStation):
                req.dist_list.append(distance_dic[dic_key(stn.loc, req.loc)])
            else:
                req.dist_list.append(distance_dic[dic_key(req.loc, stn.loc)])

        spare_time = (sum(req.dist_list)/len(req.dist_list)) / req.speed

        req.time_wdw[1] += spare_time
    # ==================================================================


    while any(req.done is False for req in req_list):
        not_completed_reqs = list(filter(lambda x: (x.done is False), req_list))
        pri_req = min(not_completed_reqs,key = lambda x: (x.start_time))
        servable_stn = list(filter(lambda x: x.can_recharge is True, stn_list))

        pri_req, pri_stn = priority(pri_req,servable_stn) # 재혁

        try:
             pri_stn.recharge(pri_req)
        except Exception:
            raise Exception('Invalid Logic')
            break

    solution['Snapshop_Requests'] = req_list
    solution['Snapshop_Stations'] = stn_list

    total_wait = 0
    total_distance = 0
    max_stn = max(stn_list, key= lambda x: x.measures['total_time'])
    total_tardiness = 0

    for stn in stn_list:
        total_distance += stn.measures['total_distance']
        total_wait += stn.measures['total_wait']

    for req in req_list:
        total_tardiness += req.tardiness

    solution['Objective'] = []
    solution['Objective'].append(total_tardiness)
    solution['Objective'].append(max_stn.measures['total_time'])
    solution['Objective'].append(total_wait)
    solution['Objective'].append((total_distance))


    return solution
