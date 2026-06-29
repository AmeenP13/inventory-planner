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
        'recommentated':''
        }
    result=graph.invoke(state)
    print('\nAI Recommendation')
    print(result['recommentated'])

