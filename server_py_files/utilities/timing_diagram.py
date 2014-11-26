
import pdb

class TimingDiagram:

    def print_diagram(self, xtsm_object):
        pdb.set_trace()
        seq = xtsm_object.XTSM.getActiveSequence()
        cMap=seq.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
        #channelHeir=cMap.createTimingGroupHeirarchy()        
        #channelRes=cMap.findTimingGroupResolutions()
        #Parser out put node. Use TimingProffer
        #Control arrays hold what is actually coming out.
        seq.collectTimingProffers()
        edge_timings = seq.TimingProffer.data['Edge']
        
        class Edge:
            def __init__(self, timing_group, channel_number, time, value, tag,
                         name, initial_value, holding_value):
                self.timing_group = timing_group
                self.channel_number = channel_number
                self.time = time
                self.value = value
                self.tag = tag
                self.max = 0
                self.min = 0
                self.name = name
                self.holding_value = holding_value
                self.initial_value = initial_value
                
            def is_same(self,edge):
                if ((self.timing_group == edge.timing_group) and
                (self.channel_number == edge.channel_number) and
                (self.time == edge.time) and
                (self.value == edge.value) and
                (self.tag == edge.tag)):
                    return True
                else:
                    return False
            
        edges = []
        longest_name = 0
        for edge in edge_timings:
            for channel in cMap.Channel:
                tgroup = int(channel.TimingGroup.PCDATA)
                tgroupIndex = int(channel.TimingGroupIndex.PCDATA)
                if tgroup == int(edge[0]) and tgroupIndex == int(edge[1]):
                    name = channel.ChannelName.PCDATA
                    init_val = ''
                    hold_val = ''
                    try:
                        init_val = channel.InitialValue.PCDATA
                    except AttributeError:
                        init_val = 'None '
                    try:
                        hold_val = channel.HoldingValue.PCDATA
                    except AttributeError:
                        hold_val = 'None '
                    if len(name) > longest_name:
                        longest_name = len(name)
                    edges.append(Edge(edge[0],edge[1],edge[2],edge[3],edge[4],
                                      name, init_val,hold_val))
                    #pdb.set_trace()
            
        unique_group_channels = []
        for edge in edges:
            is_found = False
            for ugc in unique_group_channels:
                if edge.is_same(ugc):
                    is_found = True
            if not is_found:
                unique_group_channels.append(edge)
                
                
        from operator import itemgetter
        edge_timings_by_group = sorted(edge_timings, key=itemgetter(2))
        edge_timings_by_group_list = []
        for edge in edge_timings_by_group:
            edge_timings_by_group_list.append(edge.tolist())
        #print edge_timings
        for p in edge_timings_by_group_list: print p   
        
        unique_times = []
        for edge in edges:
            is_found = False
            for t in unique_times:
                if edge.time == t.time:
                    is_found = True
            if not is_found:
                unique_times.append(edge)        
        
        
        #pdb.set_trace()
        for ugc in unique_group_channels:
            s = ugc.name.rjust(longest_name)
            current_edge = edges[0]
            previous_edge = edges[0]
            is_first = True
            for t in unique_times:
                is_found = False
                for edge in edges:
                    if edge.timing_group == ugc.timing_group and edge.channel_number == ugc.channel_number and edge.time == t.time:
                        is_found = True
                        current_edge = edge
                if is_first:
                    s = s + '|' + str('%7s' % str(current_edge.initial_value))
                    is_first = False
                    previous_edge.value = current_edge.initial_value
                    if previous_edge.value == 'None ':
                        previous_edge.value = 0
                if is_found:
                    if current_edge.value > previous_edge.value:
                        s += '^' + str('%7s' % str(current_edge.value))
                    else:
                        s += 'v' + str('%7s' % str(current_edge.value))
                    previous_edge = current_edge
                else:
                    s += '|' + '.'*7
            s = s + '|' + str('%7s' % str(current_edge.holding_value))
            print s             
                       
                       
        s = "Time (ms)".rjust(longest_name) + '|' + str('%7s' % str("Initial"))
        for t in unique_times:
            s += '|' + str('%7s' % str(t.time))
        s = s + '|' + str('%7s' % str("Holding"))
        print s
        
    
