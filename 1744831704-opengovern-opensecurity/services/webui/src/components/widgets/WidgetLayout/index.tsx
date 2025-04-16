import { useAtom, useSetAtom } from 'jotai'
import { LayoutAtom, meAtom, notificationAtom } from '../../../store'
import * as React from 'react'
import Board from '@cloudscape-design/board-components/board'
import BoardItem from '@cloudscape-design/board-components/board-item'
import Header from '@cloudscape-design/components/header'
import {
    Alert,
    Button,
    ButtonDropdown,
    Checkbox,
    FormField,
    Input,
    Modal,
    Spinner,
} from '@cloudscape-design/components'
import { useEffect, useState } from 'react'
import TableWidget from '../table'
import axios from 'axios'
import ChartWidget from '../charts'
import KeyValueWidget from '../KeyValue'
import { array } from 'prop-types'
import Shortcuts from '../Shortcuts'
import Integrations from '../Integrations'
import SRE from '../KPI_Cards'

const COMPONENT_MAPPING = {
    table: TableWidget,
    chart: ChartWidget,
    kpi: KeyValueWidget,
    shortcut: Shortcuts,
    integration: Integrations,
    sre: SRE
}
const NUMBER_MAPPING = {
    0: 'First',
    1: 'Second',
    2: 'Third',
    3: 'Fourth',
    4: 'Fifth',
}
export interface Layout {
    id:           string;
    data:         Data;
    rowSpan:      number;
    columnSpan:   number;
    columnOffset: ColumnOffset;
}

export interface ColumnOffset {
    "4": number;
}

export interface Data {
    componentId: string;
    title:       string;
    description: string;
    props:       any;
}

export interface WidgetLayoutProps {
    input_layout: any
    is_default: boolean
    HandleAddItem:Function
}


export default function WidgetLayout({
    input_layout,
    is_default,
    HandleAddItem,
}: WidgetLayoutProps) {
    const [layout, setLayout] = useState(input_layout)
    const [me, setMe] = useAtom(meAtom)
    const [items, setItems] = useState<Layout[]>([])
    const [layoutLoading, setLayoutLoading] = useState<boolean>(false)
    const [addModalOpen, setAddModalOpen] = useState(false)
    const [selectedAddItem, setSelectedAddItem] = useState<any>('')
    const [widgetProps, setWidgetProps] = useState<any>({})
    const [isEdit, setIsEdit] = useState(false)
    const [editId, setEditId] = useState('')
    const [openEditLayout, setOpenEditLayout] = useState(false)
    const [editLayout, setEditLayout] = useState<any>()
    const setNotification = useSetAtom(notificationAtom)
    useEffect(() => {
        if (layout) {
            // add to ietms
            console.log(layout,"layout")
            if (layout?.widgets){
            setItems(layout?.widgets)

            } else{
                setItems([])
            }
        }
    }, [layout])
    const GetComponent = (name: string, props: any) => {
        // @ts-ignore
        const Component = COMPONENT_MAPPING[name]
        if (Component) {
            return <Component {...props} />
        }
        return null
    }
    const SetDefaultLayout = (layout_config: any) => {
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
        const body = {
            id: layout?.id,
            is_default: layout.is_default,
            user_id: me?.username,
            layout_config: layout_config,
            name: layout.name,
            description: layout.description,
            is_private: layout.is_private,
        }

        axios
            .post(`${url}/main/core/api/v4/layout/set`, body, config)
            .then((res) => {})
            .catch((err) => {
                console.log(err)
            })
    }
    const GetDefaultLayout = () => {
        setLayoutLoading(true)
        axios
            .get(
                `https://raw.githubusercontent.com/opengovern/platform-configuration/refs/heads/main/default_layout.json`
            )
            .then((res) => {
                setLayout(res?.data)
                setLayoutLoading(false)
            })
            .catch((err) => {
                setLayoutLoading(false)
            })
    }
    const HandleRemoveItemByID = (id: string) => {
        const newItems = items.filter((item: any) => item.id !== id)
        setItems(newItems)
    }
    const HandleWidgetProps = () => {
        if (selectedAddItem == 'table') {
            return (
                <>
                    <FormField label="Table query ID">
                        <Input
                            placeholder="Table query ID"
                            value={widgetProps?.query_id}
                            onChange={(e: any) => {
                                setWidgetProps({
                                    ...widgetProps,
                                    query_id: e.detail.value,
                                })
                            }}
                        />
                    </FormField>
                    <FormField label="Page size">
                        <Input
                            placeholder="Page size"
                            value={widgetProps?.display_rows}
                            onChange={(e: any) => {
                                setWidgetProps({
                                    ...widgetProps,
                                    display_rows: e.detail.value,
                                })
                            }}
                        />
                    </FormField>
                </>
            )
        }
        if (selectedAddItem == 'kpi') {
            return (
                <>
                    {/* map 4 times and return 3 input count_kpi info list_kpi all of them inside kpies key */}
                    {[0, 1, 2, 3,4,5].map((item, index: number) => {
                        return (
                            <div key={index} className="flex flex-row gap-6">
                                {index == 0 ? (
                                    <>
                                        {' '}
                                        <FormField label={` KPI Name`}>
                                            <Input
                                                placeholder={`   KPI Name`}
                                                value={
                                                    widgetProps?.kpis?.[index]
                                                        ?.info
                                                }
                                                onChange={(e: any) => {
                                                    HandleKPIPropChange(index,e.detail.value,'info')

                                                }}
                                            />
                                        </FormField>
                                        <FormField label={`  Count Query ID`}>
                                            <Input
                                                placeholder={`   Count Query ID`}
                                                value={
                                                    widgetProps?.kpis?.[index]
                                                        ?.count_kpi
                                                }
                                                onChange={(e: any) => {
                                                    HandleKPIPropChange(index,e.detail.value,'count_kpi')
                                                }}
                                            />
                                        </FormField>
                                        <FormField label={`  List Query ID`}>
                                            <Input
                                                placeholder={`   List Query ID`}
                                                value={
                                                    widgetProps?.kpis?.[index]
                                                        ?.list_kpi
                                                }
                                                onChange={(e: any) => {
                                                    HandleKPIPropChange(index,e.detail.value,'list_kpi')
                                                }}
                                            />
                                        </FormField>
                                    </>
                                ) : (
                                    <>
                                        {' '}
                                            <Input
                                                placeholder={`   KPI Name`}
                                                value={
                                                    widgetProps?.kpis?.[index]
                                                        ?.info
                                                }
                                                onChange={(e: any) => {
                                                    HandleKPIPropChange(
                                                        index,
                                                        e.detail.value,
                                                        'info'
                                                    )
                                                }}
                                            />
                                            <Input
                                                placeholder={`   Count Query ID`}
                                                value={
                                                    widgetProps?.kpis?.[index]
                                                        ?.count_kpi
                                                }
                                                onChange={(e: any) => {
                                                    HandleKPIPropChange(
                                                        index,
                                                        e.detail.value,
                                                        'count_kpi'
                                                    )
                                                }}
                                            />
                                            <Input
                                                placeholder={`   List Query ID`}
                                                value={
                                                    widgetProps?.kpis?.[index]
                                                        ?.list_kpi
                                                }
                                                onChange={(e: any) => {
                                                    HandleKPIPropChange(
                                                        index,
                                                        e.detail.value,
                                                        'list_kpi'
                                                    )
                                                }}
                                            />
                                    </>
                                )}
                            </div>
                        )
                    })}
                </>
            )
        }
    }
    const HandleAddWidget = () => {
        if (!widgetProps?.title || !widgetProps?.description) {
            return
        }
        const newItem = {
            id: `${selectedAddItem}-${items?.length}`,
            data: {
                componentId: selectedAddItem,
                props: widgetProps,
                title: widgetProps?.title,
                description: widgetProps?.description,
            },
            rowSpan: 2,
            columnSpan: 2,
            columnOffset: { '4': 0 },
        }
        // @ts-ignore
        setItems([...items, newItem])
        setAddModalOpen(false)
        setWidgetProps({})
    }
    const HandleAddProductWidgets = (id: string) => {
        // check if id not exist in items
        const check = items.filter((item: any) => item.id === id)
        if (check.length > 0) {
            setNotification({
                text: `Widget Already exist`,
                type: 'error',
            })
            return
        }
        if (id == 'integration') {
            const new_item = {
                id: 'integration',
                data: {
                    componentId: 'integration',
                    title: 'Integrations',
                    description: '',
                    props: {},
                },
                rowSpan: 8,
                columnSpan: 1,
                columnOffset: { '4': 3 },
            }
            setItems([...items, new_item])
        }
        if (id == 'shortcut') {
            const new_item = {
                id: 'shortcut',
                data: {
                    componentId: 'shortcut',
                    title: 'Shortcuts',
                    description: '',
                    props: {},
                },
                rowSpan: 2,
                columnSpan: 3,
                columnOffset: { '4': 0 },
            }
            setItems([...items, new_item])
        }
        if (id == 'sre') {
            const new_item = {
                id: 'sre',
                data: {
                    componentId: 'sre',
                    title: 'SRE',
                    description: '',
                    props: {},
                },
                rowSpan: 2,
                columnSpan: 3,
                columnOffset: { '4': 0 },
            }
            setItems([...items, new_item])
        }
        return
    }
    const GetWidgetSettingsItem = (id: string) => {
        if (id == 'sre' || id == 'shortcut' || id == 'integration') {
            return [{ id: 'remove', text: 'Remove' }]
        } else {
            return [
                { id: 'remove', text: 'Remove' },
                {
                    id: 'edit',
                    text: 'Edit',
                },
            ]
        }
    }
    const HandleEditWidget = () => {
        const temp_items = items
        // find item with editId
        const index = items.findIndex((item: any) => item.id === editId)
        const newItem = {
            id: editId,
            data: {
                componentId: selectedAddItem,
                props: widgetProps,
                title: widgetProps?.title,
                description: widgetProps?.description,
            },
            rowSpan: temp_items[index].rowSpan,
            columnSpan: temp_items[index].columnSpan,
            columnOffset: temp_items[index].columnOffset,
        }
        temp_items[index] = newItem
        setItems(temp_items)
        setAddModalOpen(false)
        setWidgetProps({})
        setIsEdit(false)
        setEditId('')
        setSelectedAddItem('')
    }
    const HandleKPIPropChange = (index: number, value: string, key: string) => {
        console.log(index,value,key)
        const currentKPIs = widgetProps?.kpis ?? []

        // Clone the KPI list or extend it to the required length
        const updatedKPIs = [...currentKPIs]

        // If the item at index doesn't exist, initialize it as an object
        if (!updatedKPIs[index]) {
            updatedKPIs[index] = {}
        }

        // Set or update the specific key-value pair
        updatedKPIs[index] = {
            ...updatedKPIs[index],
            [key]: value,
        }
        console.log(updatedKPIs)
        // Update widgetProps safely
        setWidgetProps({
            ...(widgetProps ?? {}),
            kpis: updatedKPIs,
        })
    }

    return (
        <div className="w-full h-full flex flex-col gap-8">
            <Header
                variant="h3"
                // description={}
                actions={
                    <div className="flex flex-row gap-2">
                        {/* <ButtonDropdown
                            items={[
                                { id: 'add', text: 'Add new dashboard' },

                                { id: 'save', text: 'Save' },
                                { id: 'edit', text: 'Edit' },
                                {
                                    id: 'reset',
                                    text: 'Reset to default layout',
                                },
                            ]}
                            onItemClick={(event: any) => {
                                if (event.detail.id == 'add') {
                                    HandleAddItem()
                                }
                                if (event.detail.id == 'reset') {
                                    GetDefaultLayout()
                                }
                                if (event.detail.id == 'save') {
                                    SetDefaultLayout(items)
                                }
                                if (event.detail.id == 'edit') {
                                    setEditLayout(layout)
                                    setOpenEditLayout(true)
                                }
                            }}
                            ariaLabel="Board item settings"
                        >
                            Dashboard settings
                        </ButtonDropdown>
                        <ButtonDropdown
                            items={[
                                { id: 'table', text: 'Table Widget' },
                                { id: 'chart', text: 'Pie Chart Widget' },
                                { id: 'kpi', text: 'KPI Widget' },
                                { id: 'integration', text: 'Integrations' },
                                { id: 'shortcut', text: 'Shortcuts' },
                                { id: 'sre', text: 'SRE' },
                            ]}
                            onItemClick={(event: any) => {
                                if (
                                    event.detail.id == 'sre' ||
                                    event.detail.id == 'shortcut' ||
                                    event.detail.id == 'integration'
                                ) {
                                    HandleAddProductWidgets(event.detail.id)
                                } else {
                                    setSelectedAddItem(event.detail.id)
                                    setAddModalOpen(true)
                                }
                            }}
                            ariaLabel="Board item settings"
                        >
                            Add Widget
                        </ButtonDropdown> */}
                    </div>
                }
            >
                <span className=" font-normal "> {layout?.description}</span>
            </Header>
            {layoutLoading ? (
                <Spinner />
            ) : (
                <Board
                    renderItem={(item: any) => (
                        <BoardItem
                            header={
                                <Header description={item?.data?.description}>
                                    {item.data.title}
                                </Header>
                            }
                            settings={
                                <ButtonDropdown
                                    items={GetWidgetSettingsItem(item.id)}
                                    onItemClick={(event) => {
                                        if (event.detail.id === 'remove') {
                                            HandleRemoveItemByID(item.id)
                                        }
                                        if (event.detail.id === 'edit') {
                                            setIsEdit(true)
                                            setWidgetProps({
                                                title: item?.data?.title,
                                                description:
                                                    item?.data?.description,
                                                ...item?.data?.props,
                                            })
                                            setSelectedAddItem(
                                                item?.data?.componentId
                                            )
                                            setEditId(item.id)
                                            setAddModalOpen(true)
                                        }
                                    }}
                                    ariaLabel="Board item settings"
                                    variant="icon"
                                />
                            }
                            i18nStrings={{
                                dragHandleAriaLabel: 'Drag handle',
                                dragHandleAriaDescription:
                                    'Use Space or Enter to activate drag, arrow keys to move, Space or Enter to submit, or Escape to discard. Be sure to temporarily disable any screen reader navigation feature that may interfere with the functionality of the arrow keys.',
                                resizeHandleAriaLabel: 'Resize handle',
                                resizeHandleAriaDescription:
                                    'Use Space or Enter to activate resize, arrow keys to move, Space or Enter to submit, or Escape to discard. Be sure to temporarily disable any screen reader navigation feature that may interfere with the functionality of the arrow keys.',
                            }}
                        >
                            {GetComponent(
                                item?.data?.componentId,
                                item?.data?.props
                            )}
                        </BoardItem>
                    )}
                    onItemsChange={(event: any) => {
                        setItems(event.detail.items)
                    }}
                    // @ts-ignore
                    items={items}
                    empty={
                        <div className="flex flex-col items-center justify-center w-full h-full">
                            <span className="text-gray-500">No items</span>
                        </div>
                    }
                    i18nStrings={(() => {
                        function createAnnouncement(
                            operationAnnouncement: any,
                            conflicts: any,
                            disturbed: any
                        ) {
                            const conflictsAnnouncement =
                                //
                                conflicts?.length > 0
                                    ? `Conflicts with ${conflicts
                                          .map((c: any) => c.data.title)
                                          .join(', ')}.`
                                    : ''
                            const disturbedAnnouncement =
                                disturbed.length > 0
                                    ? `Disturbed ${disturbed.length} items.`
                                    : ''
                            return [
                                operationAnnouncement,
                                conflictsAnnouncement,
                                disturbedAnnouncement,
                            ]
                                .filter(Boolean)
                                .join(' ')
                        }
                        return {
                            liveAnnouncementDndStarted: (operationType) =>
                                operationType === 'resize'
                                    ? 'Resizing'
                                    : 'Dragging',
                            liveAnnouncementDndItemReordered: (operation) => {
                                const columns = `column ${
                                    operation.placement.x + 1
                                }`
                                const rows = `row ${operation.placement.y + 1}`
                                return createAnnouncement(
                                    `Item moved to ${
                                        operation.direction === 'horizontal'
                                            ? columns
                                            : rows
                                    }.`,
                                    operation.conflicts,
                                    operation.disturbed
                                )
                            },
                            liveAnnouncementDndItemResized: (operation) => {
                                const columnsConstraint =
                                    operation.isMinimalColumnsReached
                                        ? ' (minimal)'
                                        : ''
                                const rowsConstraint =
                                    operation.isMinimalRowsReached
                                        ? ' (minimal)'
                                        : ''
                                const sizeAnnouncement =
                                    operation.direction === 'horizontal'
                                        ? `columns ${operation.placement.width}${columnsConstraint}`
                                        : `rows ${operation.placement.height}${rowsConstraint}`
                                return createAnnouncement(
                                    `Item resized to ${sizeAnnouncement}.`,
                                    operation.conflicts,
                                    operation.disturbed
                                )
                            },
                            liveAnnouncementDndItemInserted: (operation) => {
                                const columns = `column ${
                                    operation.placement.x + 1
                                }`
                                const rows = `row ${operation.placement.y + 1}`
                                return createAnnouncement(
                                    `Item inserted to ${columns}, ${rows}.`,
                                    operation.conflicts,
                                    operation.disturbed
                                )
                            },
                            liveAnnouncementDndCommitted: (operationType) =>
                                `${operationType} committed`,
                            liveAnnouncementDndDiscarded: (operationType) =>
                                `${operationType} discarded`,
                            liveAnnouncementItemRemoved: (op: any) =>
                                createAnnouncement(
                                    `Removed item ${op.item.data.title}.`,
                                    [],
                                    op.disturbed
                                ),
                            navigationAriaLabel: 'Board navigation',
                            navigationAriaDescription:
                                'Click on non-empty item to move focus over',
                            navigationItemAriaLabel: (item: any) =>
                                item ? item.data.title : 'Empty',
                        }
                    })()}
                />
            )}
            <Modal
                visible={addModalOpen}
                onDismiss={() => {
                    setAddModalOpen(false)
                }}
                header={`${isEdit ? 'Edit' : 'Add'} ${
                    selectedAddItem?.charAt(0).toUpperCase() +
                    selectedAddItem?.slice(1)
                } Widget`}
            >
                <div className="flex flex-col gap-2">
                    <FormField label="Widget Name">
                        <Input
                            placeholder="Widget Name"
                            ariaRequired={true}
                            value={widgetProps?.title}
                            onChange={(e: any) => {
                                setWidgetProps({
                                    ...widgetProps,
                                    title: e.detail.value,
                                })
                            }}
                        />
                    </FormField>

                    <FormField label="Widget  description">
                        <Input
                            placeholder="Widget description"
                            ariaRequired={true}
                            value={widgetProps?.description}
                            onChange={(e: any) => {
                                setWidgetProps({
                                    ...widgetProps,
                                    description: e.detail.value,
                                })
                            }}
                        />
                    </FormField>

                    {HandleWidgetProps()}
                    {(!widgetProps?.title || !widgetProps?.description) && (
                        <Alert
                            type="error"
                            header="Please fill all the required fields"
                        >
                            Please fill all the required fields
                        </Alert>
                    )}
                    <div className="flex w-full justify-end items-center">
                        <Button
                            onClick={() => {
                                isEdit ? HandleEditWidget() : HandleAddWidget()
                            }}
                        >
                            {isEdit ? 'Save' : 'Submit'}
                        </Button>
                    </div>
                </div>
            </Modal>
            <Modal
                visible={openEditLayout}
                onDismiss={() => {
                    setOpenEditLayout(false)
                }}
                header={`Edit Dashboard`}
            >
                <div className="flex flex-col gap-2">
                    <FormField
                        // description="This is a description."
                        label="Dashboard Name"
                    >
                        <Input
                            placeholder="Dashboard Name"
                            ariaRequired={true}
                            value={editLayout?.name}
                            onChange={(e: any) => {
                                setEditLayout({
                                    ...editLayout,
                                    name: e.detail.value,
                                })
                            }}
                        />
                    </FormField>
                    <FormField label="Dashboard description">
                        <Input
                            placeholder="Dashboard description"
                            ariaRequired={true}
                            value={editLayout?.description}
                            onChange={(e: any) => {
                                setEditLayout({
                                    ...editLayout,
                                    description: e.detail.value,
                                })
                            }}
                        />
                    </FormField>

                    <Checkbox
                        checked={editLayout?.is_private}
                        onChange={(e: any) => {
                            setEditLayout({
                                ...editLayout,
                                is_private: e.detail.checked,
                            })
                        }}
                    >
                        Private Dashboard
                    </Checkbox>

                    <div className="flex w-full justify-end items-center">
                        <Button
                            onClick={() => {
                                setLayout(editLayout)
                                setOpenEditLayout(false)
                            }}
                        >
                            save
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    )
}
