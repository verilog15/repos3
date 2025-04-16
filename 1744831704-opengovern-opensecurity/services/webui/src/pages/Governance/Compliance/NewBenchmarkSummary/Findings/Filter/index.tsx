import { Button, Card, Col, Flex, Grid, Icon, Text } from '@tremor/react'
import { Popover, Transition } from '@headlessui/react'
import {
    CalendarIcon,
    CheckCircleIcon,
    ChevronDownIcon,
    CloudIcon,
    PlusIcon,
    TrashIcon,
    XCircleIcon,
} from '@heroicons/react/24/outline'
import { Fragment, useEffect, useState } from 'react'
import dayjs from 'dayjs'
import { useParams } from 'react-router-dom'
import Provider from './Provider'
import {
    PlatformEnginePkgComplianceApiConformanceStatus,
    SourceType,
    TypesFindingSeverity,
} from '../../../../../../api/api'
import ConformanceStatus from './ConformanceStatus'
import { useComplianceApiV1FindingsFiltersCreate } from '../../../../../../api/compliance.gen'
import Others from './Others'

import {
    CloudConnect,
    Compliance,
    Control,
    Id,
    Lifecycle,
    Resources,
    SeverityIcon,
} from '../../../../../../icons/icons'
import Severity from './Severity'
import Datepicker, { IDate } from './Datepicker'
import {
    DateRange,
    defaultEventTime,
    defaultFindingsTime,
    useURLParam,
    useUrlDateRangeState,
} from '../../../../../../utilities/urlstate'
import LimitHealthy from './LimitHealthy'
import { PropertyFilter, Select } from '@cloudscape-design/components'
import axios from 'axios'

interface IFilters {
    onApply: (obj: {
        connector: SourceType
        conformanceStatus:
            | PlatformEnginePkgComplianceApiConformanceStatus[]
            | undefined
        severity: TypesFindingSeverity[] | undefined
        connectionID: string[] | undefined
        controlID: string[] | undefined
        benchmarkID: string[] | undefined
        resourceTypeID: string[] | undefined
        lifecycle: boolean[] | undefined
        activeTimeRange: DateRange | undefined
        eventTimeRange: DateRange | undefined
        jobID: string[] | undefined
        connectionGroup: string[] | undefined
    }) => void
    type: 'findings' | 'resources' | 'controls' | 'accounts' | 'events'
    setDate: Function
}

export default function Filter({ onApply, type, setDate }: IFilters) {
    const { ws } = useParams()
    const defConnector = SourceType.Nil
    const [connector, setConnector] = useState<SourceType>(defConnector)

    const defConformanceStatus = [
        PlatformEnginePkgComplianceApiConformanceStatus.ConformanceStatusFailed,
        PlatformEnginePkgComplianceApiConformanceStatus.ConformanceStatusPassed,
    ]
    const [conformanceStatus, setConformanceStatus] = useState<
        | PlatformEnginePkgComplianceApiConformanceStatus[]
        | undefined
    >([
        PlatformEnginePkgComplianceApiConformanceStatus.ConformanceStatusFailed,
    ])

    const defLifecycle = [true]
    const [lifecycle, setLifecycle] = useState<boolean[]>(defLifecycle)

    const defSeverity = [
        TypesFindingSeverity.FindingSeverityCritical,
        TypesFindingSeverity.FindingSeverityHigh,
        TypesFindingSeverity.FindingSeverityMedium,
        TypesFindingSeverity.FindingSeverityLow,
        TypesFindingSeverity.FindingSeverityNone,
    ]
    const [severity, setSeverity] = useState<
        TypesFindingSeverity[] | undefined
    >(defSeverity)
    const [severityCon, setSeverityCon] = useState('is')

    const [connectionID, setConnectionID] = useState<string[] | undefined>([])
    const [connectionCon, setConnectionCon] = useState('is')
    const [controlID, setControlID] = useState<string[] | undefined>([])
    const [controlCon, setControlCon] = useState('is')
    const [benchmarkID, setBenchmarkID] = useState<string[] | undefined>([])
    const [benchmarkCon, setBenchmarkCon] = useState('is')
    const [resourceTypeID, setResourceTypeID] = useState<string[] | undefined>(
        []
    )
    const [resourceCon, setResourceCon] = useState('is')
    const [dateCon, setDateCon] = useState('isBetween')
    const [eventDateCon, setEventDateCon] = useState('isBetween')
    const today = new Date()
    const lastWeek = new Date(
        today.getFullYear(),
        today.getMonth(),
        today.getDate() - 7
    )
    const [activeTimeRange, setActiveTimeRange] = useState({
        start: dayjs(lastWeek),
        end: dayjs(today),
    })
    const [jobData, setJobData] = useState([])
    const [jobs, setJobs] = useState([])
    const { benchmarkId } = useParams()

    const GetJobs = () => {
        
        let url = ''
        if (window.location.origin === 'http://localhost:3000') {
            url = window.__RUNTIME_CONFIG__.REACT_APP_BASE_URL
        } else {
            url = window.location.origin
        }
        const body = {
            job_status: ['SUCCEEDED'],
            benchmark_id: [benchmarkId],
        }
        // @ts-ignore
        const token = JSON.parse(localStorage.getItem('openg_auth')).token

        const config = {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        }
        //    console.log(config)
        axios
            .post(`${url}/main//schedule/api/v3/jobs/compliance`, body, config)
            .then((res) => {
                // @ts-ignore
                const temp = []
                // @ts-ignore
                res.data?.items?.map((d) => {
                    temp.push({
                        label: d.job_id.toString(),
                        value: d.job_id.toString(),
                    })
                })
                // @ts-ignore
                setJobData(temp)
            })
            .catch((err) => {
                console.log(err)
            })
    }
    useEffect(() => {
        GetJobs()
    }, [])
    // const { value: eventTimeRange, setValue: setEventTimeRange } =
    //     useUrlDateRangeState(
    //         defaultEventTime(ws || ''),
    //         'eventStartDate',
    //         'eventEndDate'
    //     )
    const [selectedFilters, setSelectedFilters] = useState<string[]>([
        'conformance_status',
        'connectionGroup',
        'provider',
        'lifecycle',
        'severity',
        'limit_healthy',
        'connection',
        'control',
        // 'benchmark',
        'resource',
        'date',
        'eventDate',
        'job_id',
    ])

    useEffect(() => {
        // @ts-ignore
        onApply({
            connector,
            conformanceStatus,
            severity,
            connectionID,
            controlID,
            // benchmarkID,
            resourceTypeID,
            lifecycle,
            activeTimeRange: selectedFilters.includes('date')
                ? activeTimeRange
                : undefined,
            // eventTimeRange: selectedFilters.includes('eventDate')
            //     ? eventTimeRange
            //     : undefined,
        })
    }, [
        activeTimeRange,
        // eventTimeRange,
    ])
    const truncate = (text: string | undefined) => {
        if (text) {
            return text.length > 30 ? text.substring(0, 30) + '...' : text
        }
    }
    const { response: filters } = useComplianceApiV1FindingsFiltersCreate({})
    const severity_data = [
        {
            label: 'Critical',
            value: TypesFindingSeverity.FindingSeverityCritical,
            color: '#6E120B',
            iconSvg: (
                <>
                    <div
                        className="h-4 w-1.5 rounded-sm"
                        style={{
                            backgroundColor: '#6E120B',
                        }}
                    />
                </>
            ),
        },
        {
            label: 'High',
            value: TypesFindingSeverity.FindingSeverityHigh,
            color: '#CA2B1D',
            iconSvg: (
                <>
                    <div
                        className="h-4 w-1.5 rounded-sm"
                        style={{
                            backgroundColor: '#ca2b1d',
                        }}
                    />
                </>
            ),
        },
        {
            label: 'Medium',
            value: TypesFindingSeverity.FindingSeverityMedium,
            color: '#EE9235',
            iconSvg: (
                <>
                    <div
                        className="h-4 w-1.5 rounded-sm"
                        style={{
                            backgroundColor: '#ee9235',
                        }}
                    />
                </>
            ),
        },
        {
            label: 'Low',
            value: TypesFindingSeverity.FindingSeverityLow,
            color: '#F4C744',
            iconSvg: (
                <>
                    <div
                        className="h-4 w-1.5 rounded-sm"
                        style={{
                            backgroundColor: '#f4c744',
                        }}
                    />
                </>
            ),
        },
        {
            label: 'None',
            value: TypesFindingSeverity.FindingSeverityNone,
            color: '#9BA2AE',
            iconSvg: (
                <>
                    <div
                        className="h-4 w-1.5 rounded-sm"
                        style={{
                            backgroundColor: '#9ba2ae',
                        }}
                    />
                </>
            ),
        },
    ]
    const confarmance_data = [
        {
            label: 'Failed',
            value: PlatformEnginePkgComplianceApiConformanceStatus.ConformanceStatusFailed,

            iconSvg: <XCircleIcon className="h-5 text-rose-600" />,
        },
        {
            label: 'Passed',
            value: PlatformEnginePkgComplianceApiConformanceStatus.ConformanceStatusPassed,

            iconSvg: <CheckCircleIcon className="h-5 text-emerald-500" />,
        },
    ]
   const connectionGroup_data = [
       {
           label: 'Active',
           value: 'active',
       },
       {
           label: 'Inactive',
           value: 'inactive',
       },
      
   ]
    const filterOptions = [
        {
            id: 'conformance_status',
            name: 'compliance Status',
            icon: CheckCircleIcon,
            component: (
                <ConformanceStatus
                    value={conformanceStatus}
                    defaultValue={defConformanceStatus}
                    onChange={(c) => setConformanceStatus(c)}
                />
            ),
            conditions: ['is'],
            onChange: (c: any) => setConformanceStatus(c),
            setCondition: (c: string) => console.log(c),
            value: conformanceStatus,
            defaultValue: defConformanceStatus,
            onDelete: undefined,
            data: confarmance_data,
            types: ['findings', 'resources', 'events'],
        },
        // {
        //     id: 'connectionGroup',
        //     name: 'Integration Groups',
        //     icon: CheckCircleIcon,
        //     component: (
        //         <ConformanceStatus
        //             value={conformanceStatus}
        //             defaultValue={defConformanceStatus}
        //             onChange={(c) => setConformanceStatus(c)}
        //         />
        //     ),
        //     conditions: ['is'],
        //     onChange: (c: any) => setJobs(c),
        //     setCondition: (c: string) => console.log(c),
        //     value: conformanceStatus,
        //     defaultValue: defConformanceStatus,
        //     onDelete: undefined,
        //     data: connectionGroup_data,
        //     types: ['findings', 'resources', 'events'],
        // },
        {
            id: 'job_id',
            name: 'Job Id',
            icon: CheckCircleIcon,
            component: (
                <ConformanceStatus
                    value={conformanceStatus}
                    defaultValue={defConformanceStatus}
                    onChange={(c) => setConformanceStatus(c)}
                />
            ),
            conditions: ['is'],
            onChange: (c: any) => setJobs(c),
            setCondition: (c: string) => console.log(c),
            value: conformanceStatus,
            defaultValue: defConformanceStatus,
            onDelete: undefined,
            data: jobData,
            types: ['findings', 'resources', 'events'],
        },

        // {
        //     id: 'provider',
        //     name: 'Connector',
        //     icon: CloudConnect,
        //     component: (
        //         <Provider
        //             value={connector}
        //             defaultValue={defConnector}
        //             onChange={(p) => setConnector(p)}
        //         />
        //     ),
        //     conditions: ['is'],
        //     setCondition: (c: string) => undefined,
        //     value: [connector],
        //     defaultValue: [defConnector],
        //     onDelete: () => setConnector(defConnector),
        //     types: ['findings', 'resources', 'events', 'controls', 'accounts'],
        // },
        // {
        //     id: 'lifecycle',
        //     name: 'Lifecycle',
        //     icon: Lifecycle,
        //     component: (
        //         <FindingLifecycle
        //             value={lifecycle}
        //             defaultValue={defLifecycle}
        //             onChange={(l) => setLifecycle(l)}
        //         />
        //     ),
        //     conditions: ['is'],
        //     setCondition: (c: string) => console.log(c),
        //     value: lifecycle,
        //     defaultValue: defLifecycle,
        //     onDelete: () => setLifecycle(defLifecycle),
        //     types: ['findings', 'resources', 'events'],
        // },
        {
            id: 'severity',
            name: 'Severity',
            icon: SeverityIcon,
            component: (
                <Severity
                    value={severity}
                    defaultValue={defSeverity}
                    condition={severityCon}
                    onChange={(s) => setSeverity(s)}
                />
            ),
            conditions: ['is', 'isNot'],
            setCondition: (c: string) => setSeverityCon(c),
            onChange: (s: any) => setSeverity(s),
            value: severity,
            defaultValue: defSeverity,
            data: severity_data,
            onDelete: () => setSeverity(defSeverity),
            types: ['findings', 'resources', 'events'],
        },
        // {
        //     id: 'limit_healthy',
        //     name: 'Limit Healthy',
        //     icon: CheckCircleIcon,
        //     component: (
        //         <LimitHealthy
        //             value={undefined}
        //             defaultValue={undefined}
        //             onChange={(c) => {}}
        //         />
        //     ),
        //     conditions: ['is'],
        //     setCondition: (c: string) => console.log(c),
        //     value: conformanceStatus,
        //     defaultValue: defConformanceStatus,
        //     onDelete: undefined,
        //     types: ['findings', 'resources', 'events'],
        // },
        {
            id: 'connection',
            name: 'Cloud Account',
            icon: Id,
            component: (
                <Others
                    value={connectionID}
                    defaultValue={[]}
                    data={filters}
                    condition={connectionCon}
                    type="integrationID"
                    onChange={(o) => setConnectionID(o)}
                    name={'Integration'}
                />
            ),
            conditions: ['is', 'isNot'],
            setCondition: (c: string) => setConnectionCon(c),
            value: connectionID,
            onChange: (s: any) => setConnectionID(s),

            defaultValue: [],
            onDelete: () => setConnectionID([]),
            data: filters?.integrationID,
            types: ['findings', 'resources', 'events', 'controls', 'accounts'],
        },
        {
            id: 'control',
            name: 'Control',
            icon: Control,
            component: (
                <Others
                    value={controlID}
                    defaultValue={[]}
                    data={filters}
                    condition={controlCon}
                    type="controlID"
                    name={'Control'}
                    onChange={(o) => setControlID(o)}
                />
            ),
            conditions: ['is', 'isNot'],
            setCondition: (c: string) => setControlCon(c),
            value: controlID,
            defaultValue: [],
            onChange: (s: any) => setControlID(s),
            onDelete: () => setControlID([]),
            data: filters?.controlID,
            types: ['findings', 'resources', 'events'],
        },
        // {
        //     id: 'benchmark',
        //     name: 'Benchmark',
        //     icon: Compliance,
        //     component: (
        //         <Others
        //             value={benchmarkID}
        //             defaultValue={[]}
        //             data={filters}
        //             condition={benchmarkCon}
        //             type="benchmarkID"
        //             onChange={(o) => setBenchmarkID(o)}
        //             name={'Frameworks'}
        //         />
        //     ),
        //     conditions: ['is'],
        //     setCondition: (c: string) => setBenchmarkCon(c),
        //     value: benchmarkID,
        //     defaultValue: [],
        //     onChange: (s: any) => setBenchmarkCon(s),
        //     onDelete: () => setBenchmarkID([]),
        //     data: filters?.benchmarkID,
        //     types: ['findings', 'resources', 'events', 'controls', 'accounts'],
        // },
        {
            id: 'resource',
            name: 'Resource Type',
            icon: Resources,
            component: (
                <Others
                    value={resourceTypeID}
                    defaultValue={[]}
                    data={filters}
                    condition={resourceCon}
                    type="resourceTypeID"
                    onChange={(o) => setResourceTypeID(o)}
                    name={'Resource Type'}
                />
            ),
            conditions: ['is', 'isNot'],
            setCondition: (c: string) => setResourceCon(c),
            value: resourceTypeID,
            onChange: (s: any) => setResourceTypeID(s),
            defaultValue: [],
            onDelete: () => setResourceTypeID([]),
            data: filters?.resourceTypeID,
            types: ['findings', 'resources', 'events'],
        },
        {
            id: 'date',
            name: type === 'events' ? 'Audit Period' : 'Last Updated',
            icon: CalendarIcon,
            component: (
                <Datepicker
                    condition={dateCon}
                    activeTimeRange={activeTimeRange}
                    setActiveTimeRange={(v) => setActiveTimeRange(v)}
                    name={type === 'events' ? 'Audit Period' : 'Last Updated'}
                />
            ),
            conditions: ['isBetween', 'isRelative'],
            setCondition: (c: string) => setDateCon(c),
            value: activeTimeRange,
            defaultValue: { start: dayjs.utc(), end: dayjs.utc() },
            onDelete: () =>
                setActiveTimeRange({ start: dayjs.utc(), end: dayjs.utc() }),
            types: ['findings', 'events'],
        },
        // {
        //     id: 'eventDate',
        //     name: 'Last Event',
        //     icon: CalendarIcon,
        //     component: (
        //         <Datepicker
        //             condition={eventDateCon}
        //             activeTimeRange={eventTimeRange}
        //             setActiveTimeRange={(v) => setEventTimeRange(v)}
        //         />
        //     ),
        //     conditions: ['isBetween', 'isRelative'],
        //     setCondition: (c: string) => setEventDateCon(c),
        //     value: eventTimeRange,
        //     defaultValue: { start: dayjs.utc(), end: dayjs.utc() },
        //     onDelete: () =>
        //         setEventTimeRange({ start: dayjs.utc(), end: dayjs.utc() }),
        //     types: ['findings'],
        // },
    ]
    const [query, setQuery] = useState({
        tokens: [
            {
                propertyKey: 'conformance_status',
                value: 'failed',
                operator: '=',
            },
            // {
            //     propertyKey: 'connectionGroup',
            //     value: 'healthy',
            //     operator: '=',
            // },
        ],
        operation: 'and',
    })
    useEffect(() => {
        const conformance_status: any = []
        const temp_severity: any = []
        const connection: any = []
        const control: any = []
        // const benchmark: any = []
        const resource: any = []
        const job_id: any = []
        const connection_group: any = []

        query.tokens.map((t: { propertyKey: string; value: string }) => {
            if (t.propertyKey === 'conformance_status') {
                conformance_status.push(t.value)
            }
            if (t.propertyKey === 'severity') {
                temp_severity.push(t.value)
            }
            if (t.propertyKey === 'connectionGroup') {
                connection_group.push(t.value)
            }
            if (t.propertyKey === 'connection') {
                connection.push(t.value)
            }
            if (t.propertyKey === 'control') {
                control.push(t.value)
            }
            // if (t.propertyKey === 'benchmark') {
            //     benchmark.push(t.value)
            // }
            if (t.propertyKey === 'resource') {
                resource.push(t.value)
            }
            if (t.propertyKey === 'job_id') {
                job_id.push(t.value)
            }
        })
        // @ts-ignore
        onApply({
            connector,
            conformanceStatus: conformance_status,
            severity: temp_severity,
            connectionID: connection,
            controlID: control,
            // benchmarkID : benchmark,
            resourceTypeID: resource,
            lifecycle,
            jobID: job_id,
            connectionGroup: connection_group,
            activeTimeRange: selectedFilters.includes('date')
                ? activeTimeRange
                : undefined,
            // eventTimeRange: selectedFilters.includes('eventDate')
            //     ? eventTimeRange
            //     : undefined,
        })
    }, [query])
      const [filter, setFilter] = useState({
          label: 'Recent Incidents',
          value: '1',
      })
      useEffect(() => {
          // @ts-ignore
          if (filter) {
              // @ts-ignore

              if (filter.value == '1') {
                  setDate({
                      key: 'previous-3-days',
                      amount: 3,
                      unit: 'day',
                      type: 'relative',
                  })
                  setQuery({
                      tokens: [
                          {
                              propertyKey: 'conformance_status',
                              value: 'failed',
                              operator: '=',
                          },
                        //   {
                        //       propertyKey: 'connectionGroup',
                        //       value: 'healthy',
                        //       operator: '=',
                        //   },
                      ],
                      operation: 'and',
                  })
              }
              // @ts-ignore
              else if (filter.value == '2') {
                  setDate({
                      key: 'previous-3-days',
                      amount: 3,
                      unit: 'day',
                      type: 'relative',
                  })
                  setQuery({
                      tokens: [
                          {
                              propertyKey: 'severity',
                              value: 'critical',
                              operator: '=',
                          },
                          {
                              propertyKey: 'conformance_status',
                              value: 'failed',
                              operator: '=',
                          },
                        //   {
                        //       propertyKey: 'connectionGroup',
                        //       value: 'healthy',
                        //       operator: '=',
                        //   },
                      ],
                      operation: 'and',
                  })
              }
          }
      }, [filter])
    const renderFilters = () => {
        let date_filter = filterOptions.find((o) => o.id === 'date')
        let has_date = selectedFilters.includes('date')
        // @ts-ignore

        const options = []
        // @ts-ignore

        const properties = []
        selectedFilters.map((sf) => {
            const f = filterOptions.find((o) => o.id === sf)
            if (f?.types?.includes(type)) {
                properties.push({
                    key: f.id,
                    operators: ['='],
                    propertyLabel: f.name,
                    groupValuesLabel: `${f.name}  Values`,
                })
                if (
                    f.id == 'severity' ||
                    f.id == 'conformance_status' ||
                    f.id == 'job_id' ||
                    f.id == 'connectionGroup'
                ) {
                    f?.data?.map((d) => {
                        options.push({
                            propertyKey: f.id.toString(),
                            // @ts-ignore

                            label: d?.label.toString(),
                            // @ts-ignore

                            value: d?.value.toString(),
                            // @ts-ignore

                            iconSvg: d?.iconSvg?.toString(),
                        })
                    })
                } else {
                    f?.data?.map((d) => {
                        options.push({
                            propertyKey: f.id.toString(),
                            // @ts-ignore

                            label: d?.displayName.toString(),
                            // @ts-ignore

                            value: d?.key.toString(),
                        })
                    })
                }
            }
        })

        return (
            <>
                <Flex
                    flexDirection="row"
                    justifyContent="start"
                    alignItems="start"
                    className="w-fit gap-2 sm:flex-row flex-col"
                >
                    <Select
                        // @ts-ignore
                        selectedOption={filter}
                        className="sm:w-1/5 w-full mt-[-9px]"
                        inlineLabelText={'Saved Filters'}
                        placeholder="Select Filter Set"
                        // @ts-ignore
                        onChange={({ detail }) =>
                            // @ts-ignore
                            setFilter(detail.selectedOption)
                        }
                        options={[
                            { label: 'Recent Incidents', value: '1' },
                            { label: 'Recent Critical Incidents', value: '2' },
                        ]}
                    />
                    <PropertyFilter
                        // @ts-ignore
                        query={query}
                        // @ts-ignore
                        // className="w-full"
                        // @ts-ignore
                        onChange={({ detail }) => setQuery(detail)}
                        // countText="5 matches"
                        // enableTokenGroups
                        expandToViewport
                        hideOperations
                        tokenLimit={2}
                        filteringEmpty="No suggestions found"
                        filteringAriaLabel="Find Incidents"
                        // @ts-ignore
                        filteringOptions={options}
                        filteringPlaceholder="Find Incidents"
                        // @ts-ignore

                        filteringProperties={properties}
                        virtualScroll
                    />
                    {/* {has_date && (
                    <div className="w-full ">{date_filter?.component}</div>
                )} */}
                </Flex>
            </>
        )
    }

    return <>{renderFilters()}</>
}
