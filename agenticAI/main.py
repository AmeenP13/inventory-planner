from graph import graph
state=None
while True:
    user_input=input('Ask More details about product:')
    if user_input.lower().strip() in{'quit','bye','exit'}:
        print('Exisiting browser')
        break
    state={
        'message':[user_input],
        'inventory':{},
        'demand':{},
        'risk':'',
        'policy':'',
        'recommendation':''
        }
    result=graph.invoke(state)
    if 'error' in result:
        print(result['error'])
    else:
        print('\nAI Inventory Recommendation')
        print(result['recommendation'])

