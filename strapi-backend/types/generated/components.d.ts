import type { Schema, Struct } from '@strapi/strapi';

export interface SharedLocation extends Struct.ComponentSchema {
  collectionName: 'components_shared_locations';
  info: {
    displayName: 'Location';
  };
  attributes: {
    address: Schema.Attribute.String;
    latitude: Schema.Attribute.BigInteger;
    longitude: Schema.Attribute.BigInteger;
  };
}

declare module '@strapi/strapi' {
  export module Public {
    export interface ComponentSchemas {
      'shared.location': SharedLocation;
    }
  }
}
