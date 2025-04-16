import {
    Accordion,
    AccordionBody,
    AccordionHeader,
    Button,
    Card,
    Flex,
    Grid,
    Icon,
    Select,
    SelectItem,
    Tab,
    TabGroup,
    TabList,
    TabPanel,
    TabPanels,
    Text,
    TextInput,
} from '@tremor/react'
import {
    ChevronDoubleLeftIcon,
    ChevronDownIcon,
    ChevronUpIcon,
    CommandLineIcon,
    FunnelIcon,
    MagnifyingGlassIcon,
    PlayCircleIcon,
    TableCellsIcon,
} from '@heroicons/react/24/outline'
import { Fragment, useEffect, useMemo, useState } from 'react' // eslint-disable-next-line import/no-extraneous-dependencies
import { highlight, languages } from 'prismjs' // eslint-disable-next-line import/no-extraneous-dependencies
import 'prismjs/components/prism-sql' // eslint-disable-next-line import/no-extraneous-dependencies
import 'prismjs/themes/prism.css'
import {
    CheckCircleIcon,
    ExclamationCircleIcon,
} from '@heroicons/react/24/solid'
import { Transition } from '@headlessui/react'
import { useAtom, useAtomValue } from 'jotai'
import {
    useInventoryApiV1QueryList,
    useInventoryApiV1QueryRunCreate,
    useInventoryApiV2AnalyticsCategoriesList,
} from '../../../api/inventory.gen'
import Spinner from '../../../components/Spinner'
import { getErrorMessage } from '../../../types/apierror'
import { RenderObject } from '../../../components/RenderObject'

import { isDemoAtom, queryAtom, runQueryAtom } from '../../../store'
import { snakeCaseToLabel } from '../../../utilities/labelMaker'
import { numberDisplay } from '../../../utilities/numericDisplay'
import TopHeader from '../../../components/Layout/Header'
import KTable from '@cloudscape-design/components/table'
import {
    AppLayout,
    Box,
    ExpandableSection,
    Header,
    Modal,
    Pagination,
    Popover,
    SpaceBetween,
    SplitPanel,
    Tabs,
} from '@cloudscape-design/components'

import CodeEditor from '@cloudscape-design/components/code-editor'
import KButton from '@cloudscape-design/components/button'
import AllQueries from '../All Query'
import axios from 'axios'
import CustomPagination from '../../../components/Pagination'
import SQLEditor from './editor'
import { useParams, useSearchParams } from 'react-router-dom'

export const getTable = (
    headers: string[] | undefined,
    details: any[][] | undefined
) => {
    const columns: any[] = []
    const rows: any[] = []
    const column_def: any[] = []
    const headerField = headers?.map((value, idx) => {
        if (headers.filter((v) => v === value).length > 1) {
            return `${value}-${idx}`
        }
        return value
    })
    if (headers && headers.length) {
        for (let i = 0; i < headers.length; i += 1) {
            const isHide = headers[i][0] === '_'
            // columns.push({
            //     field: headerField?.at(i),
            //     headerName: snakeCaseToLabel(headers[i]),
            //     type: 'string',
            //     sortable: true,
            //     hide: isHide,
            //     resizable: true,
            //     filter: true,
            //     width: 170,
            //     cellRenderer: (param: ValueFormatterParams) => (
            //         <span className={isDemo ? 'blur-sm' : ''}>
            //             {param.value}
            //         </span>
            //     ),
            // })
            columns.push({
                id: headerField?.at(i),
                header: snakeCaseToLabel(headers[i]),
                // @ts-ignore
                cell: (item: any) => (
                    <>
                        {/* @ts-ignore */}
                        {typeof item[headerField?.at(i)] == 'string'
                            ? // @ts-ignore
                              item[headerField?.at(i)]
                            : // @ts-ignore
                              JSON.stringify(item[headerField?.at(i)])}
                    </>
                ),
                maxWidth: '200px',
                // sortingField: 'id',
                // isRowHeader: true,
                // maxWidth: 150,
            })
            column_def.push({
                id: headerField?.at(i),
                visible: !isHide,
            })
        }
    }
    if (details && details.length) {
        for (let i = 0; i < details.length; i += 1) {
            const row: any = {}
            for (let j = 0; j < columns.length; j += 1) {
                row[headerField?.at(j) || ''] = details[i][j]
                //     typeof details[i][j] === 'string'
                //         ? details[i][j]
                //         : JSON.stringify(details[i][j])
            }
            rows.push(row)
        }
    }
    const count = rows.length

    return {
        columns,
        column_def,
        rows,
        count,
    }
}

export default function Query() {
    const [runQuery, setRunQuery] = useAtom(runQueryAtom)
    const [loaded, setLoaded] = useState(false)
    const [savedQuery, setSavedQuery] = useAtom(queryAtom)
    const [code, setCode] = useState(savedQuery ? savedQuery : '')
    const [selectedIndex, setSelectedIndex] = useState(0)
    const [searchCategory, setSearchCategory] = useState('')
    const [selectedRow, setSelectedRow] = useState({})
    const [openDrawer, setOpenDrawer] = useState(false)
    const [showEditor, setShowEditor] = useState(true)
    const [pageSize, setPageSize] = useState(1000)
    const [autoRun, setAutoRun] = useState(false)
    const [navigationOpen, setNavigationOpen] = useState(true)

    const [page, setPage] = useState(0)
    const [searchParams, setSearchParams] = useSearchParams()
    const [tab, setTab] = useState('0')
    const [preferences, setPreferences] = useState(undefined)
    const [integrations, setIntegrations] = useState([])
    const [selectedIntegration, setSelectedIntegration] = useState('')
    const [tables, setTables] = useState([])
    const [suggestTables, setSuggestTables] = useState([])
    const [selectedTable, setSelectedTable] = useState('')
    const [columns, setColumns] = useState([])
    const [schemaLoading, setSchemaLoading] = useState(false)
    const [schemaLoading1, setSchemaLoading1] = useState(false)
    const [schemaLoading2, setSchemaLoading2] = useState(false)
    const [expanded, setExpanded] = useState(-1)
    const [expanded1, setExpanded1] = useState(-1)
    const [openIntegration, setOpenIntegration] = useState(false)
    const [openLayout, setOpenLayout] = useState(true)
    const [splitSize, setSplitSize] = useState(1200)
    const [tables1, setTables1] = useState([
        {
            table: 'users',
            columns: ['id', 'name', 'email'],
        },
        {
            table: 'orders',
            columns: ['id', 'user_id', 'amount'],
        },
    ])

    // const { response: categories, isLoading: categoryLoading } =
    //     useInventoryApiV2AnalyticsCategoriesList()

    const {
        response: queryResponse,
        isLoading,
        isExecuted,
        sendNow,
        sendNowWithParams,
        error,
    } = useInventoryApiV1QueryRunCreate(
        {
            page: { no: 1, size: pageSize },
            // @ts-ignore
            engine: 'cloudql',
            query: code,
        },
        {},
        autoRun
    )

    useEffect(() => {
        if (autoRun) {
            setAutoRun(false)
        }
        if (queryResponse?.query?.length) {
            setSelectedIndex(2)
        } else setSelectedIndex(0)
    }, [queryResponse])

    useEffect(() => {
        if (!loaded && code.length > 0) {
            sendNow()
            setLoaded(true)
        }
    }, [page])

    useEffect(() => {
        if (code.length) setShowEditor(true)
    }, [code])

    const memoCount = useMemo(
        () => getTable(queryResponse?.headers, queryResponse?.result).count,
        [queryResponse]
    )

    useEffect(() => {
        if (savedQuery.length > 0 && savedQuery !== '') {
            setCode(savedQuery)
            setAutoRun(true)
            setOpenLayout(false)
        }
    }, [savedQuery])
    useEffect(() => {
        const id = searchParams.get('query_id')

        if (id) {
            sendNowWithParams(
                {
                    page: { no: 1, size: 1000 },
                    // @ts-ignore
                    engine: 'cloudql',
                    query_id: id,
                    use_cache: true,
                },
                {}
            )
            setOpenLayout(false)
        }
    }, [])

    const getIntegrations = () => {
        setSchemaLoading(true)
        let url = ''
        if (window.location.origin === 'http://localhost:3000') {
            url = window.__RUNTIME_CONFIG__.REACT_APP_BASE_URL
        } else {
            url = window.location.origin
        }
        // @ts-ignore
        const token = JSON.parse(localStorage.getItem('openg_auth')).token

        const config = {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        }

        axios
            .get(
                `${url}/main/integration/api/v1/integration-types/plugin`,
                config
            )
            .then((res) => {
                if (res.data) {
                    const arr = res.data?.items
                    const temp: any = []
                    // arr.sort(() => Math.random() - 0.5);
                    arr?.map((integration: any) => {
                        if (integration.source_code !== '') {
                            temp.push(integration)
                        }
                    })
                    setIntegrations(temp)
                }
                setSchemaLoading(false)
            })
            .catch((err) => {
                setSchemaLoading(false)
            })
    }
    const getMasterSchema = (id: string) => {
        let url = ''
        if (window.location.origin === 'http://localhost:3000') {
            url = window.__RUNTIME_CONFIG__.REACT_APP_BASE_URL
        } else {
            url = window.location.origin
        }
        // @ts-ignore
        const token = JSON.parse(localStorage.getItem('openg_auth')).token

        const config = {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        }
        setSchemaLoading1(true)
        axios
            .get(
                `${url}/main/integration/api/v1/integration-types/${id}/table`,
                config
            )
            .then((res) => {
                if (res.data) {
                    setTables(res.data?.tables)
                }
                setSchemaLoading1(false)
            })
            .catch((err) => {
                setSchemaLoading1(false)
            })
    }
    useEffect(() => {
        const temp = suggestTables
        Object.entries(tables)?.map((item, index) => {
            const entri = {
                table: item[0],
                // @ts-ignore
                columns: item[1]?.map((column: any) => column.Name),
            }
            // @ts-ignore

            temp.push(entri)
        })
        setSuggestTables(temp)
    }, [tables])

    useEffect(() => {
        getIntegrations()
    }, [])
    const RunCode = (query: string) => {
        setLoaded(true)
        setPage(0)
        sendNowWithParams(
            {
                page: { no: 1, size: pageSize },
                // @ts-ignore
                engine: 'cloudql',
                query: query,
            },
            {}
        )
    }

    return (
        <>
            <Modal
                visible={openDrawer}
                onDismiss={() => setOpenDrawer(false)}
                header="Query Result"
                className="min-w-[500px]"
                size="large"
            >
                <RenderObject obj={selectedRow} />
            </Modal>
            <Header
                className={`   rounded-xl mb-4    ${
                    false ? 'rounded-b-none' : ''
                }`}
                variant="h1"
                description={
                    <div className="group  important text-black  relative sm:flex hidden text-wrap justify-start">
                        Query all discovered assets across clouds and
                        integrations in SQL.
                    </div>
                }
            >
                CloudQL
            </Header>
            <AppLayout
                toolsOpen={false}
                navigationOpen={navigationOpen}
                onNavigationChange={(event) => {
                    setNavigationOpen(event.detail.open)
                }}
                navigation={
                    <>
                        <Flex
                            flexDirection="col"
                            justifyContent="start"
                            alignItems="start"
                            className="gap-2 overflow-y-scroll w-full mt-2 "
                        >
                            <Text className="text-base text-black flex flex-row justify-between w-full">
                                <span className="w-full">Plugin schema</span>
                            </Text>
                            <>
                                {schemaLoading ? (
                                    <>
                                        <Spinner />
                                    </>
                                ) : (
                                    <>
                                        {integrations?.map(
                                            (integration: any, index) => {
                                                return (
                                                    <>
                                                        {/*   prettier-ignore */}
                                                        {
                                                            //  prettier-ignore
                                                            (integration.install_state ==
                                                                    'installed' &&
                                                                integration.operational_status ==
                                                                    'enabled') ? (
                                                                    <>
                                                                        <ExpandableSection
                                                                            expanded={
                                                                                expanded ==
                                                                                index
                                                                            }
                                                                            onChange={({
                                                                                detail,
                                                                            }) => {
                                                                                if (
                                                                                    detail.expanded
                                                                                ) {
                                                                                    setExpanded(
                                                                                        index
                                                                                    )
                                                                                    setSelectedIntegration(
                                                                                        integration
                                                                                    )
                                                                                    getMasterSchema(
                                                                                        integration.plugin_id
                                                                                    )
                                                                                } else {
                                                                                    setExpanded(
                                                                                        -1
                                                                                    )
                                                                                }
                                                                            }}
                                                                            headerText={
                                                                                <span className=" text-sm font-normal ">
                                                                                    {
                                                                                        integration?.name
                                                                                    }
                                                                                </span>
                                                                            }
                                                                        >
                                                                            <>
                                                                                {schemaLoading1 ? (
                                                                                    <>
                                                                                        <Spinner />
                                                                                    </>
                                                                                ) : (
                                                                                    <div className="ml-4">
                                                                                        {' '}
                                                                                        <>
                                                                                            {tables &&
                                                                                                Object.entries(
                                                                                                    tables
                                                                                                )?.map(
                                                                                                    (
                                                                                                        item: any,
                                                                                                        index1
                                                                                                    ) => {
                                                                                                        return (
                                                                                                            <>
                                                                                                                <ExpandableSection
                                                                                                                    expanded={
                                                                                                                        expanded1 ==
                                                                                                                        index1
                                                                                                                    }
                                                                                                                    onChange={({
                                                                                                                        detail,
                                                                                                                    }) => {
                                                                                                                        if (
                                                                                                                            detail.expanded
                                                                                                                        ) {
                                                                                                                            setExpanded1(
                                                                                                                                index1
                                                                                                                            )
                                                                                                                            setSelectedTable(
                                                                                                                                item[0]
                                                                                                                            )
                                                                                                                            setColumns(
                                                                                                                                item[1]
                                                                                                                            )
                                                                                                                        } else {
                                                                                                                            setExpanded1(
                                                                                                                                -1
                                                                                                                            )
                                                                                                                        }
                                                                                                                    }}
                                                                                                                    headerText={
                                                                                                                        <span
                                                                                                                            onClick={(
                                                                                                                                e
                                                                                                                            ) => {
                                                                                                                                e.preventDefault()
                                                                                                                                e.stopPropagation()
                                                                                                                                setCode(
                                                                                                                                    code +
                                                                                                                                        `${item[0]}`
                                                                                                                                )
                                                                                                                            }}
                                                                                                                            className=" text-sm font-normal"
                                                                                                                        >
                                                                                                                            {
                                                                                                                                item[0]
                                                                                                                            }
                                                                                                                        </span>
                                                                                                                    }
                                                                                                                >
                                                                                                                    <>
                                                                                                                        {schemaLoading2 ? (
                                                                                                                            <>
                                                                                                                                <Spinner />
                                                                                                                            </>
                                                                                                                        ) : (
                                                                                                                            <>
                                                                                                                                {columns?.map(
                                                                                                                                    (
                                                                                                                                        column: any,
                                                                                                                                        index2
                                                                                                                                    ) => {
                                                                                                                                        return (
                                                                                                                                            <>
                                                                                                                                                <Flex className="pl-6 w-full">
                                                                                                                                                    <span className=" font-normal text-sm">
                                                                                                                                                        {
                                                                                                                                                            column.Name
                                                                                                                                                        }
                                                                                                                                                    </span>
                                                                                                                                                    <span>
                                                                                                                                                        (
                                                                                                                                                        {
                                                                                                                                                            column.Type
                                                                                                                                                        }

                                                                                                                                                        )
                                                                                                                                                    </span>
                                                                                                                                                </Flex>
                                                                                                                                            </>
                                                                                                                                        )
                                                                                                                                    }
                                                                                                                                )}
                                                                                                                            </>
                                                                                                                        )}
                                                                                                                    </>
                                                                                                                </ExpandableSection>
                                                                                                            </>
                                                                                                        )
                                                                                                    }
                                                                                                )}
                                                                                        </>
                                                                                    </div>
                                                                                )}
                                                                            </>
                                                                        </ExpandableSection>
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                      <span  onClick={(e)=>{
                                                                        setSelectedIntegration(
                                                                            integration
                                                                        )
                                                                        setOpenIntegration(true)
                                                                          
                                                                      }} className=" text-sm text-gray-400  ml-5 cursor-pointer">
                                                                                    {
                                                                                        integration?.name
                                                                                    }
                                                                                </span>
                                                                    </>
                                                                )
                                                        }
                                                    </>
                                                )
                                            }
                                        )}
                                    </>
                                )}
                            </>
                        </Flex>
                    </>
                }
                contentType="table"
                className="w-full"
                toolsHide={true}
                navigationHide={false}
                splitPanelOpen={openLayout}
                onSplitPanelToggle={() => {
                    setOpenLayout(!openLayout)
                }}
                splitPanelSize={splitSize}
                onSplitPanelResize={({ detail }) => {
                    setSplitSize(detail.size)
                }}
                splitPanel={
                    // @ts-ignore
                    <SplitPanel
                        // @ts-ignore
                        header={<>Saved Queries</>}
                    >
                        <>
                            <AllQueries
                                setTab={setTab}
                                setOpenLayout={setOpenLayout}
                                sendNowWithParams={sendNowWithParams}
                                setCode={setCode}
                            />
                        </>
                    </SplitPanel>
                }
                content={
                    <>
                        <Flex className="flex-col gap-2 h-full">
                            <Flex className={`h-full  w-full  `}>
                                <SQLEditor
                                    value={code}
                                    onChange={(value: any, event: any) => {
                                        setSavedQuery('')
                                        setCode(value)
                                        setOpenLayout(false)

                                        if (tab !== '3') {
                                            setTab('3')
                                        }
                                    }}
                                    tables={suggestTables}
                                    tableFetch={(name: string) => {
                                        getMasterSchema(name)
                                    }}
                                    run={RunCode}
                                />
                            </Flex>
                            <Flex flexDirection="col" className="w-full ">
                                <Flex flexDirection="col" className="mb-4">
                                    <Flex className="w-full mt-4">
                                        {/* <Flex
                                            justifyContent="start"
                                            className="gap-1"
                                        >
                                            <Text className="mr-2 w-fit">
                                                Maximum rows:
                                            </Text>
                                            <Select
                                                enableClear={false}
                                                className="w-44"
                                                placeholder="1,000"
                                            >
                                                <SelectItem
                                                    value="1000"
                                                    onClick={() =>
                                                        setPageSize(1000)
                                                    }
                                                >
                                                    1,000
                                                </SelectItem>
                                                <SelectItem
                                                    value="3000"
                                                    onClick={() =>
                                                        setPageSize(3000)
                                                    }
                                                >
                                                    3,000
                                                </SelectItem>
                                                <SelectItem
                                                    value="5000"
                                                    onClick={() =>
                                                        setPageSize(5000)
                                                    }
                                                >
                                                    5,000
                                                </SelectItem>
                                                <SelectItem
                                                    value="10000"
                                                    onClick={() =>
                                                        setPageSize(10000)
                                                    }
                                                >
                                                    10,000
                                                </SelectItem>
                                            </Select>
                                        </Flex> */}
                                        <Flex className="w-full gap-x-3 justify-end">
                                            {!!code.length && (
                                                <KButton
                                                    className="  w-max min-w-max  "
                                                    onClick={() => setCode('')}
                                                    iconSvg={
                                                        <CommandLineIcon className="w-5 " />
                                                    }
                                                >
                                                    Clear editor
                                                </KButton>
                                            )}
                                            <Popover
                                                content="Press Shift+Enter to run query."
                                                dismissButton={false}
                                                position="top"
                                                size="small"
                                                triggerType="custom"
                                            >
                                                <KButton
                                                    // icon={PlayCircleIcon}
                                                    variant="primary"
                                                    className="w-max  min-w-[400px]  "
                                                    onClick={() => {
                                                        sendNow()
                                                        setLoaded(true)
                                                        setPage(0)
                                                    }}
                                                    disabled={!code.length}
                                                    loading={
                                                        isLoading && isExecuted
                                                    }
                                                    loadingText="Running"
                                                    iconSvg={
                                                        <PlayCircleIcon className="w-5 " />
                                                    }
                                                >
                                                    Run
                                                </KButton>
                                            </Popover>
                                        </Flex>
                                    </Flex>
                                    <Flex className="w-full">
                                        {!isLoading && isExecuted && error && (
                                            <Flex
                                                justifyContent="start"
                                                className="w-fit"
                                            >
                                                <Icon
                                                    icon={ExclamationCircleIcon}
                                                    color="rose"
                                                />
                                                <Text color="rose">
                                                    {getErrorMessage(error)}
                                                </Text>
                                            </Flex>
                                        )}
                                        {!isLoading &&
                                            isExecuted &&
                                            queryResponse && (
                                                <Flex
                                                    justifyContent="start"
                                                    className="w-fit"
                                                >
                                                    {memoCount === pageSize ? (
                                                        <>
                                                            <Icon
                                                                icon={
                                                                    ExclamationCircleIcon
                                                                }
                                                                color="amber"
                                                                className="ml-0 pl-0"
                                                            />
                                                            <Text color="amber">
                                                                {`Row limit of ${numberDisplay(
                                                                    pageSize,
                                                                    0
                                                                )} reached, results are truncated`}
                                                            </Text>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Icon
                                                                icon={
                                                                    CheckCircleIcon
                                                                }
                                                                color="emerald"
                                                            />
                                                            <Text color="emerald">
                                                                Success
                                                            </Text>
                                                        </>
                                                    )}
                                                </Flex>
                                            )}
                                    </Flex>
                                </Flex>
                                <Grid numItems={1} className="w-full">
                                    <KTable
                                        className="   min-h-[450px]   "
                                        // resizableColumns
                                        variant="full-page"
                                        renderAriaLive={({
                                            firstIndex,
                                            lastIndex,
                                            totalItemsCount,
                                        }) =>
                                            `Displaying items ${firstIndex} to ${lastIndex} of ${totalItemsCount}`
                                        }
                                        onSortingChange={(event) => {
                                            // setSort(event.detail.sortingColumn.sortingField)
                                            // setSortOrder(!sortOrder)
                                        }}
                                        // sortingColumn={sort}
                                        // sortingDescending={sortOrder}
                                        // sortingDescending={sortOrder == 'desc' ? true : false}
                                        // @ts-ignore
                                        // stickyHeader={true}
                                        resizableColumns={true}
                                        // stickyColumns={
                                        //  {   first:1,
                                        //     last: 1}
                                        // }
                                        onRowClick={(event) => {
                                            const row = event.detail.item
                                            // @ts-ignore
                                            setSelectedRow(row)
                                            setOpenDrawer(true)
                                        }}
                                        columnDefinitions={
                                            getTable(
                                                queryResponse?.headers,
                                                queryResponse?.result
                                            ).columns
                                        }
                                        columnDisplay={
                                            getTable(
                                                queryResponse?.headers,
                                                queryResponse?.result
                                            ).column_def
                                        }
                                        enableKeyboardNavigation
                                        // @ts-ignore
                                        items={getTable(
                                            queryResponse?.headers,
                                            queryResponse?.result
                                        ).rows?.slice(
                                            page * 10,
                                            (page + 1) * 10
                                        )}
                                        loading={isLoading}
                                        loadingText="Loading resources"
                                        // stickyColumns={{ first: 0, last: 1 }}
                                        // stripedRows
                                        trackBy="id"
                                        empty={
                                            <Box
                                                margin={{
                                                    vertical: 'xs',
                                                }}
                                                textAlign="center"
                                                color="inherit"
                                            >
                                                <SpaceBetween size="m">
                                                    <b>No Results</b>
                                                </SpaceBetween>
                                            </Box>
                                        }
                                        header={
                                            <Header className="w-full">
                                                Results{' '}
                                                <span className=" font-medium">
                                                    {isLoading && isExecuted
                                                        ? '(?)'
                                                        : `(${memoCount})`}{' '}
                                                </span>
                                            </Header>
                                        }
                                        pagination={
                                            <CustomPagination
                                                currentPageIndex={page + 1}
                                                pagesCount={
                                                    // prettier-ignore
                                                    (isLoading &&
                                                            isExecuted)
                                                                ? 0
                                                                : Math.ceil(
                                                                      // @ts-ignore
                                                                      getTable(
                                                                          queryResponse?.headers,
                                                                          queryResponse?.result
                                                                      ).rows
                                                                          .length /
                                                                          10
                                                                  )
                                                }
                                                onChange={({ detail }: any) =>
                                                    setPage(
                                                        detail.currentPageIndex -
                                                            1
                                                    )
                                                }
                                            />
                                        }
                                    />
                                </Grid>
                            </Flex>
                        </Flex>
                    </>
                }
            />

            <Modal
                visible={openIntegration}
                onDismiss={() => setOpenIntegration(false)}
                header="Plugin Installation"
            >
                <div className="p-4">
                    <Text>
                        This plugin is not available. Plugins need to be
                        {/* @ts-ignore */}
                        {selectedIntegration?.install_state == 'not_installed'
                            ? ' installed'
                            : ' enabled'}{' '}
                        to fetch the schema.
                    </Text>

                    <Flex
                        justifyContent="end"
                        alignItems="center"
                        flexDirection="row"
                        className="gap-3"
                    >
                        <Button
                            // loading={loading}
                            disabled={false}
                            onClick={() => setOpenIntegration(false)}
                            className="mt-6"
                        >
                            Close
                        </Button>
                    </Flex>
                </div>
            </Modal>
        </>
    )
}
