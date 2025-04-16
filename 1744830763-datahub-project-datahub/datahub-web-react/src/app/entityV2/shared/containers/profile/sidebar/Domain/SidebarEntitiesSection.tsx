import React, { useEffect } from 'react';
import styled from 'styled-components/macro';
import { useHistory } from 'react-router';
import { useEntityContext, useEntityData } from '../../../../../../entity/shared/EntityContext';
import { SidebarSection } from '../SidebarSection';
import { useEntityRegistry } from '../../../../../../useEntityRegistry';
import { getContentsSummary, getContentsSummaryText, navigateToDomainEntities } from './utils';
import { useGetDomainEntitySummaryQuery } from '../../../../../../../graphql/domain.generated';
import SidebarEntitiesLoadingSection from './SidebarEntitiesLoadingSection';
import EmptySectionText from '../EmptySectionText';
import { REDESIGN_COLORS } from '../../../../constants';

const Section = styled.div`
    display: flex;
    align-items: start;
    justify-content: start;
    flex-wrap: wrap;
`;

const SummaryText = styled.div`
    margin-right: 8px;
    text-wrap: wrap;
`;

const ViewAllButton = styled.div`
    display: flex;
    align-items: center;
    font-weight: bold;
    padding: 0px 2px;
    color: ${REDESIGN_COLORS.DARK_GREY};
    :hover {
        cursor: pointer;
    }
`;

const SidebarEntitiesSection = () => {
    const { urn, entityType } = useEntityData();
    const entityRegistry = useEntityRegistry();
    const { entityState } = useEntityContext();
    const history = useHistory();
    const { data, loading, refetch } = useGetDomainEntitySummaryQuery({
        variables: {
            urn,
        },
    });

    const shouldRefetch = entityState?.shouldRefetchContents;
    useEffect(() => {
        if (shouldRefetch) {
            refetch();
            entityState?.setShouldRefetchContents(false);
        }
    }, [shouldRefetch, entityState, refetch]);

    const contentsSummary = data?.aggregateAcrossEntities && getContentsSummary(data.aggregateAcrossEntities as any);
    const contentsCount = contentsSummary?.total || 0;
    const hasContents = contentsCount > 0;

    return (
        <SidebarSection
            title="Contents"
            key="Contents"
            content={
                <>
                    {loading && <SidebarEntitiesLoadingSection />}
                    {!loading &&
                        (hasContents ? (
                            <>
                                <Section>
                                    <SummaryText>
                                        {getContentsSummaryText(contentsSummary as any, entityRegistry)}
                                    </SummaryText>
                                    <ViewAllButton
                                        onClick={() =>
                                            navigateToDomainEntities(urn, entityType, history, entityRegistry)
                                        }
                                    >
                                        View all
                                    </ViewAllButton>
                                </Section>
                            </>
                        ) : (
                            <EmptySectionText message="No contents yet" />
                        ))}
                </>
            }
        />
    );
};

export default SidebarEntitiesSection;
