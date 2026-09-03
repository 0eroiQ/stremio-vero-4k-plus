// Based on Stremio Web. Copyright (C) 2017-2023 Smart code 203358507

import React, { forwardRef } from 'react';
import { Section } from '../components';
import User from './User';

type Props = {
    profile: Profile,
};

// Vero runs as a fullscreen TV appliance without a desktop web browser.
// Keep account actions that stay inside Stremio and omit outbound web actions.
const General = forwardRef<HTMLDivElement, Props>(({ profile }: Props, ref) => (
    <Section ref={ref}>
        <User profile={profile} />
    </Section>
));

export default General;
