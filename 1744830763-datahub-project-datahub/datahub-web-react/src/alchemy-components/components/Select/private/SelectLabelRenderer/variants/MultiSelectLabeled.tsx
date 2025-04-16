import React from 'react';
import { Pill } from '@components';
import { ActionButtonsContainer, LabelsWrapper, SelectValue } from '../../../components';
import { SelectLabelVariantProps, SelectOption } from '../../../types';

export default function MultiSelectLabeled<OptionType extends SelectOption>({
    selectedOptions,
    label,
}: SelectLabelVariantProps<OptionType>) {
    return (
        <LabelsWrapper shouldShowGap={false}>
            <ActionButtonsContainer>
                <SelectValue>{label}</SelectValue>
                {selectedOptions.length > 0 && <Pill label={`${selectedOptions.length}`} size="sm" variant="filled" />}
            </ActionButtonsContainer>
        </LabelsWrapper>
    );
}
