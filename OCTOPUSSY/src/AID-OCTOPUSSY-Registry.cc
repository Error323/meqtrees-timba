    // This file is generated automatically -- do not edit
    // Generated by /home/oms/LOFAR/autoconf_share/../DMI/src/build_aid_maps.pl
    #include "DMI/AtomicID.h"
    #include "DMI/TypeInfo.h"
    #include "DMI/DynamicTypeManager.h"
    #include "DMI/Packer.h"

    int aidRegistry_OCTOPUSSY ()
    {
      return 1;
    }

static AtomicID::Register aid_reg_AppManager(-1267,"AppManager");
static AtomicID::Register aid_reg_AppManagerWP(-1287,"AppManagerWP");
static AtomicID::Register aid_reg_Start(-1134,"Start");
static AtomicID::Register aid_reg_Stop(-1138,"Stop");
static AtomicID::Register aid_reg_Launch(-1262,"Launch");
static AtomicID::Register aid_reg_Halt(-1265,"Halt");
static AtomicID::Register aid_reg_Launched(-1263,"Launched");
static AtomicID::Register aid_reg_Halted(-1281,"Halted");
static AtomicID::Register aid_reg_App(-1137,"App");
static AtomicID::Register aid_reg_Fail(-1266,"Fail");
static AtomicID::Register aid_reg_ID(-1285,"ID");
static AtomicID::Register aid_reg_Address(-1297,"Address");
static AtomicID::Register aid_reg_Parameters(-1282,"Parameters");
static AtomicID::Register aid_reg_Argv(-1049,"Argv");
static AtomicID::Register aid_reg_ConnectionMgrWP(-1048,"ConnectionMgrWP");
static AtomicID::Register aid_reg_GWServerWP(-1081,"GWServerWP");
static AtomicID::Register aid_reg_GWClientWP(-1091,"GWClientWP");
static AtomicID::Register aid_reg_GatewayWP(-1050,"GatewayWP");
static AtomicID::Register aid_reg_Timestamp(-1032,"Timestamp");
static AtomicID::Register aid_reg_GW(-1079,"GW");
static AtomicID::Register aid_reg_Client(-1094,"Client");
static AtomicID::Register aid_reg_Server(-1061,"Server");
static AtomicID::Register aid_reg_Bind(-1066,"Bind");
static AtomicID::Register aid_reg_Error(-1071,"Error");
static AtomicID::Register aid_reg_Fatal(-1089,"Fatal");
static AtomicID::Register aid_reg_Bound(-1056,"Bound");
static AtomicID::Register aid_reg_Remote(-1063,"Remote");
static AtomicID::Register aid_reg_Up(-1074,"Up");
static AtomicID::Register aid_reg_Down(-1076,"Down");
static AtomicID::Register aid_reg_Network(-1055,"Network");
static AtomicID::Register aid_reg_Type(-1098,"Type");
static AtomicID::Register aid_reg_Duplicate(-1065,"Duplicate");
static AtomicID::Register aid_reg_Host(-1083,"Host");
static AtomicID::Register aid_reg_Port(-1082,"Port");
static AtomicID::Register aid_reg_Peers(-1057,"Peers");
static AtomicID::Register aid_reg_Connected(-1070,"Connected");
static AtomicID::Register aid_reg_Connection(-1073,"Connection");
static AtomicID::Register aid_reg_Add(-1087,"Add");
static AtomicID::Register aid_reg_Local(-1059,"Local");
static AtomicID::Register aid_reg_Open(-1069,"Open");
static AtomicID::Register aid_reg_Subscriptions(-1044,"Subscriptions");
static AtomicID::Register aid_reg_Init(-1092,"Init");
static AtomicID::Register aid_reg_Heartbeat(-1068,"Heartbeat");
static AtomicID::Register aid_reg_Reconnect(-1101,"Reconnect");
static AtomicID::Register aid_reg_FailConnect(-1085,"FailConnect");
static AtomicID::Register aid_reg_Reopen(-1058,"Reopen");
static AtomicID::Register aid_reg_List(-1053,"List");
static AtomicID::Register aid_reg_Hosts(-1078,"Hosts");
static AtomicID::Register aid_reg_Ports(-1051,"Ports");
static AtomicID::Register aid_reg_Gateway(-1046,"Gateway");
static AtomicID::Register aid_reg_LoggerWP(-1099,"LoggerWP");
static AtomicID::Register aid_reg_Max(-1149,"Max");
static AtomicID::Register aid_reg_Level(-1264,"Level");
static AtomicID::Register aid_reg_Scope(-1234,"Scope");
static AtomicID::Register aid_reg_Message(-1067,"Message");
#include "Message.h"
static TypeInfoReg::Register ti_reg_Message(-1067,TypeInfo(TypeInfo::DYNAMIC,0));
BlockableObject * __construct_Message (int n) { return n>0 ? new Message [n] : new Message; }
static DynamicTypeManager::Register dtm_reg_Message(-1067,__construct_Message);
static AtomicID::Register aid_reg_Index(-1045,"Index");
static AtomicID::Register aid_reg_Text(-1269,"Text");
static AtomicID::Register aid_reg_Dispatcher(-1097,"Dispatcher");
static AtomicID::Register aid_reg_Publish(-1077,"Publish");
static AtomicID::Register aid_reg_ReflectorWP(-1100,"ReflectorWP");
static AtomicID::Register aid_reg_Reflect(-1064,"Reflect");
static AtomicID::Register aid_reg_MsgLog(-1340,"MsgLog");
static AtomicID::Register aid_reg_LogNormal(-1345,"LogNormal");
static AtomicID::Register aid_reg_LogWarning(-1341,"LogWarning");
static AtomicID::Register aid_reg_LogError(-1344,"LogError");
static AtomicID::Register aid_reg_LogFatal(-1342,"LogFatal");
static AtomicID::Register aid_reg_LogDebug(-1343,"LogDebug");
static AtomicID::Register aid_reg_WP(-1093,"WP");
static AtomicID::Register aid_reg_Event(-1060,"Event");
static AtomicID::Register aid_reg_Timeout(-1088,"Timeout");
static AtomicID::Register aid_reg_Input(-1075,"Input");
static AtomicID::Register aid_reg_Signal(-1062,"Signal");
static AtomicID::Register aid_reg_Subscribe(-1096,"Subscribe");
static AtomicID::Register aid_reg_Hello(-1086,"Hello");
static AtomicID::Register aid_reg_Bye(-1047,"Bye");
static AtomicID::Register aid_reg_State(-1052,"State");

